# Configuration

All configuration is loaded from `.env` via `pydantic-settings` (`backend/app/config.py`). This document explains what each variable does. For copy-pasteable defaults, use `.env.example` directly — this page won't be kept byte-for-byte in sync with it.

Variables marked **(code default)** are not present in `.env.example` but have a working default in `config.py`; set them in `.env` only if you need to override that default.

## Application

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `APP_NAME` | Display name used in the FastAPI OpenAPI schema | Meeting Summarizer | Optional |
| `DEBUG` | Enables debug mode | False | Optional |
| `CORS_ORIGINS` | JSON array string of allowed frontend origins | '["http://localhost:3000"]' | Optional |

## Database

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `DATABASE_URL` | Async SQLAlchemy connection string for PostgreSQL | postgresql+asyncpg://postgres:postgres@db:5432/meeting_summarizer | Required |

## Redis

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `REDIS_URL` | Redis connection string, used for caching and as the ARQ job queue transport | redis://redis:6379/0 | Required |

## Object Storage (MinIO)

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `STORAGE_INTERNAL_ENDPOINT` | MinIO endpoint used by backend/worker containers | http://minio:9000 | Required |
| `STORAGE_PUBLIC_ENDPOINT` | MinIO endpoint used when generating presigned URLs the browser will call directly | http://localhost:9000 | Required |
| `STORAGE_ACCESS_KEY` | MinIO access key | minioadmin | Required |
| `STORAGE_SECRET_KEY` | MinIO secret key | minioadmin | Required |
| `STORAGE_BUCKET` | Bucket name; created automatically on backend startup if missing | meetings | Required |
| `STORAGE_REGION` | Region string (MinIO ignores this but boto3 requires one) | us-east-1 | Optional |
| `STORAGE_QUOTA_BYTES` (code default) | Soft storage quota | 10737418240 (10 GB) | Optional |

## File Limits

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `MAX_FILE_SIZE_BYTES` | Max upload size accepted | 2147483648 (2 GB) | Optional |
| `PRESIGN_EXPIRY_SECONDS` | How long presigned upload/download URLs stay valid | 900 (15 min) | Optional |

## ASR

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `ASR_PROVIDER` | Selects the ASR backend; this deployment runs local Faster-Whisper | local | Optional |
| `ASR_MODEL` | Faster-Whisper model size | small | Optional |
| `WHISPER_DEVICE` | Inference device | cpu | Optional |
| `WHISPER_COMPUTE_TYPE` | CTranslate2 compute type | int8 | Optional |
| `ASR_CHUNK_DURATION_SECONDS` | Length of each audio chunk sent to Whisper | 300 | Optional |
| `ASR_CHUNK_OVERLAP_SECONDS` | Overlap between consecutive chunks, used for boundary deduplication | 15 | Optional |
| `ASR_CONCURRENCY` | Max chunks transcribed in parallel | 4 | Optional |
| `ASR_TIMEOUT_SECONDS` | Per-chunk transcription timeout | 120 | Optional |
| `ASR_MAX_RETRIES` | Retry attempts per chunk | 3 | Optional |

## Diarization

Diarization is disabled by default and runs against an external service — see [diarization.md](diarization.md) for the full setup.

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `DIARIZATION_ENABLED` | Turns diarization on/off for the pipeline | false | Optional (feature toggle) |
| `DIARIZATION_PROVIDER` (code default) | Diarization backend selector | remote | Optional |
| `DIARIZATION_REMOTE_URL` | Base URL of the external diarization service (no trailing `/diarize`) | https://xxxx.ngrok-free.app | Required if enabled |
| `DIARIZATION_API_KEY` | Shared bearer token, must match the remote service | `<shared-secret>` | Required if enabled |
| `DIARIZATION_TIMEOUT_SECONDS` (code default) | Client-side request timeout | 1800 | Optional |
| `DIARIZATION_NUM_SPEAKERS` (code default) | Forces a fixed speaker count if set; otherwise inferred | unset | Optional |
| `DIARIZATION_MODEL` (code default) | Recorded in job metrics for traceability | pyannote/speaker-diarization-community-1 | Optional |

## Embeddings

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `EMBEDDING_PROVIDER` | Embedding backend; this deployment uses Ollama/Nomic | nomic | Optional |
| `EMBEDDING_MODEL` | Ollama model tag | nomic-embed-text | Optional |
| `EMBEDDING_DIMENSIONS` | Vector width — must match the pgvector column dimension in the schema | 768 | Required to match schema |
| `EMBEDDING_BATCH_SIZE` | Chunks embedded per request | 32 | Optional |
| `EMBEDDING_TIMEOUT_SECONDS` | Per-batch timeout | 60 | Optional |
| `EMBEDDING_MAX_RETRIES` | Retry attempts per batch | 3 | Optional |
| `EMBEDDING_MAX_INPUT_TOKENS` | Max tokens per embedding input | 8191 | Optional |

## LLM & RAG

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `LLM_PROVIDER` | LLM backend; this deployment uses Ollama | ollama | Optional |
| `OLLAMA_BASE_URL` | Ollama server address, reachable from inside the containers | http://host.docker.internal:11434 | Required |
| `LLM_MODEL` (code default) | Ollama model tag used for chat | gemma3:4b | Optional |
| `LLM_TEMPERATURE` (code default) | Sampling temperature | 0.2 | Optional |
| `LLM_TIMEOUT_SECONDS` (code default) | Chat completion timeout | 120 | Optional |
| `RAG_TOP_K` (code default) | Number of transcript chunks retrieved per question | 10 | Optional |
| `RAG_SIMILARITY_THRESHOLD` (code default) | Minimum similarity considered for retrieval relevance | 0.35 | Optional |
| `CHAT_HISTORY_TURNS` (code default) | Prior chat turns included as context | 6 | Optional |

## Transcript Chunking

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `TRANSCRIPT_CHUNK_MAX_TOKENS` | Max tokens per semantic chunk | 800 | Optional |
| `TRANSCRIPT_CHUNK_OVERLAP_TOKENS` | Token overlap between adjacent chunks | 80 | Optional |
| `TOKENIZER_ENCODING` | tiktoken encoding used for counting | cl100k_base | Optional |

## Worker

| Variable | Purpose | Example | Required |
|---|---|---|---|
| `MEDIA_TEMP_DIR` | Scratch directory for downloaded/extracted media | `/tmp/meeting-summarizer` | Optional |
| `PROCESSING_MAX_ATTEMPTS` | Max retries for a failed job | 3 | Optional |
| `PROCESSING_JOB_TIMEOUT_SECONDS` (code default) | Hard timeout for an entire pipeline run | 10800 (3 hr) | Optional |
| `MAX_MEDIA_DURATION_SECONDS` | Rejects recordings longer than this | 7200 (2 hr) | Optional |
| `MAX_TEMP_STORAGE_BYTES` | Cap on temp-dir usage | 5368709120 (5 GB) | Optional |
| `PROCESSING_PIPELINE_VERSION` | Version tag recorded on job metrics | 2.0 | Optional |

## Unused Variables in .env.example

`GROQ_API_KEY` and `OPENAI_API_KEY` appear under the secrets section of `.env.example` but are not currently read by Settings or called anywhere in this deployment. They can be left blank.

## Required vs Optional Summary

**Required to start the stack at all:**
* `DATABASE_URL`
* `REDIS_URL`
* `STORAGE_INTERNAL_ENDPOINT`
* `STORAGE_PUBLIC_ENDPOINT`
* `STORAGE_ACCESS_KEY`
* `STORAGE_SECRET_KEY`
* `STORAGE_BUCKET`
* `OLLAMA_BASE_URL`

**Required only if you enable diarization:**
* `DIARIZATION_ENABLED=true`
* `DIARIZATION_REMOTE_URL`
* `DIARIZATION_API_KEY`

Everything else has a working default and only needs to change if you're tuning behavior (model choice, chunk sizes, timeouts, retry limits).
