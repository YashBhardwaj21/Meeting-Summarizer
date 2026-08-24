# Architecture

## System Overview

Lumi is split into a synchronous request path (frontend → API) and an asynchronous processing path (API → queue → worker). The API never blocks on transcription, diarization, or embedding — it enqueues a job and returns immediately.

```text
                    ┌──────────────┐
                    │   React UI   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   FastAPI    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         PostgreSQL      Redis         MinIO
         + pgvector     (queue)     Media Storage
                           │
                           ▼
                    ┌──────────────┐
                    │  ARQ Worker  │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    ▼              ▼
              Speech-to-Text   Diarization
                    │              │
                    └──────┬───────┘
                           ▼
                  Speaker-aware
                    Transcript
                           │
                           ▼
                       Chunking
                           │
                           ▼
                      Embeddings
                           │
                           ▼
                     pgvector
                           │
                           ▼
                    Ollama / LLM
                           │
                           ▼
                       Answer
```

## Services

| Service | Role |
|---|---|
| **Frontend** | React UI — upload, meeting list, transcript viewer, chat |
| **API (FastAPI)** | Handles HTTP requests, presigns uploads, enqueues jobs, serves RAG answers |
| **Worker (ARQ)** | Runs the full processing pipeline per meeting; one worker container, one queue |
| **PostgreSQL + pgvector** | Stores meetings, jobs, transcripts, chat messages, and chunk embeddings |
| **Redis** | ARQ job queue |
| **MinIO** | S3-compatible object storage for uploaded media |
| **Ollama** | Serves both the embedding model (`nomic-embed-text`) and the LLM (`Gemma`) |
| **Remote diarization** | External HTTP service running Pyannote (not part of Docker Compose) — see [diarization.md](diarization.md) |

## Upload Flow

1. Frontend requests a presigned PUT URL → `POST /api/v1/files/presign`
2. Frontend uploads the file directly to MinIO using that URL
3. Frontend confirms the upload → `POST /api/v1/files/complete`
4. Backend creates a `Meeting` + `ProcessingJob` and enqueues it on Redis (via arq)
5. Worker picks up the job

*The file goes browser → MinIO directly; it does not pass through the FastAPI process.*

## Processing Pipeline

The worker runs each job through these stages in order (as tracked in `ProcessingJob.stage`):

1. `downloading`
2. `media_inspection`
3. `audio_extraction`
4. `transcription`
5. `persist_transcript_early` ← transcript is saved before diarization runs
6. `diarization` ← skipped entirely if `DIARIZATION_ENABLED=false`
7. `persist_transcript_speakers` ← transcript re-saved with speaker labels
8. `chunking`
9. `embedding`
10. `persist_index`

**Details worth noting:**
* **Transcription** splits audio into overlapping chunks, transcribes each chunk in parallel (bounded by `ASR_CONCURRENCY`), corrects timestamps back to the original timeline, and deduplicates text in the overlap regions using fuzzy matching.
* **Persist transcript (early)** is a checkpoint: the transcript is queryable even if diarization fails or is disabled.
* **Diarization** is optional. If enabled, word-level ASR timestamps are aligned against speaker turns to split segments at speaker boundaries; if diarization is disabled, every segment has no speaker.
* **Chunking** produces semantically grouped chunks (not fixed-size windows) sized by token count (`TRANSCRIPT_CHUNK_MAX_TOKENS`), using `tiktoken` for counting.
* **Embedding** batches chunks (`EMBEDDING_BATCH_SIZE`) through Ollama's embedding endpoint.
* **Persist index** is the durable checkpoint — chunks and embeddings are written together, keyed by the meeting's chat.
* The job records per-stage timings and provider metadata (ASR model, embedding model, diarization model) as metrics for observability.
* Jobs are retried with exponential backoff (5s, 15s, 45s) up to `PROCESSING_MAX_ATTEMPTS`, and can be cancelled mid-run — each stage checks for cancellation before starting.

## Question Answering / RAG Flow

Chat is scoped per meeting (each meeting has one chat workspace).

```text
 User question 
      │ 
      ▼ 
 Embed the question (follow-up aware: prepends the previous user turn to the query before embedding, for better retrieval on short follow-ups) 
      │ 
      ▼ 
 pgvector cosine-similarity search over TranscriptChunk.embedding, filtered to the chat, ordered by distance, top-k (RAG_TOP_K) 
      │ 
      ▼ 
 Fetch the underlying transcript segments for the retrieved chunks (speaker + timestamp per segment) 
      │ 
      ▼ 
 Build a context block: time-ranged, speaker-labeled transcript excerpts + prior chat history (last CHAT_HISTORY_TURNS turns) 
      │ 
      ▼ 
 Ollama chat completion (Gemma), grounded by a system prompt that requires the model to answer only from the supplied evidence 
      │ 
      ▼ 
 Answer + structured source list (chunk id, time range, speakers)
```

If no chunks exist for a chat (meeting still processing, or processing failed before indexing), the API returns a fixed message rather than calling the LLM.

## Service Communication

| From | To | Protocol |
|---|---|---|
| Frontend | Backend | HTTPS/HTTP, REST (`VITE_API_BASE_URL`) |
| Frontend | MinIO | HTTP, direct presigned PUT/GET (uploads/downloads bypass the backend) |
| Backend / Worker | PostgreSQL | asyncpg over `DATABASE_URL` |
| Backend / Worker | Redis | redis async client over `REDIS_URL`; also the ARQ job queue transport |
| Backend / Worker | MinIO | boto3 S3 API, internal endpoint for backend/worker, public endpoint for presigned URLs |
| Worker | Ollama | httpx, REST — `/api/chat` for LLM generation, embedding endpoint for `nomic-embed-text` |
| Worker | Remote diarization | httpx, HTTPS, multipart POST to `{DIARIZATION_REMOTE_URL}/diarize`, bearer-token authenticated |

## Data Flow

* **Meeting** — one row per uploaded recording; tracks status (`transcript_ready`, etc.) and duration.
* **File** — the uploaded object's storage key, size, and content type.
* **ProcessingJob** — one per meeting's processing run; tracks status, stage, attempt count, and metrics.
* **TranscriptSegment** — individual utterances with start/end time, speaker, and text.
* **TranscriptChunk** — semantic groupings of segments, each with an embedding vector, scoped to a chat.
* **Chat / ChatMessage** — the RAG conversation history for a meeting.

All processing state is persisted incrementally (see the two transcript-persist checkpoints above), so a meeting remains inspectable even if a later pipeline stage fails.
