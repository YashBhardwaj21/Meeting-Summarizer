# Diarization Service

## Overview

Lumi does not run Pyannote inside Docker Compose. Speaker diarization is handled by a separate, GPU-backed HTTP service that Lumi's worker calls over the network.

```text
 Lumi Worker 
      │ 
      │ HTTPS + Bearer token
      ▼ 
    ngrok
      │ 
      ▼ 
 Google Colab T4
      │ 
      ▼ 
 FastAPI /diarize
      │ 
      ▼ 
 Pyannote Community-1
      │ 
      ▼ 
 Speaker segments 
      │ 
      ▼ 
 Lumi Worker
```

## Why External Diarization

* Pyannote is GPU-intensive; running it in-process would force the entire stack onto a GPU host.
* Lumi's main stack (API, worker, ASR) runs on CPU.
* A Colab T4 provides practical, free-tier GPU inference for the diarization workload.
* The service is reached over an authenticated HTTP endpoint, so it can run anywhere that can expose a port — Colab/ngrok is one option, not a hard requirement.

## Requirements

* Google Colab with a T4 GPU runtime
* Hugging Face account and access token (to load the Pyannote model)
* ngrok account and authtoken (to expose the Colab runtime publicly)
* Lumi running locally with `DIARIZATION_ENABLED=true`
* Python dependencies required by the diarization service (see your notebook)

## Colab Setup

### 1. Enable T4 GPU
Runtime → Change runtime type → T4 GPU

Verify:
```python
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
```
Expected:
`True` 
`Tesla T4`

### 2. Install Dependencies
TODO: paste the exact install command(s) from your working notebook here. Do not approximate package versions — this section should stay synchronized with the notebook that is actually running.

### 3. Configure Hugging Face
```python
import os
from getpass import getpass
os.environ["HF_TOKEN"] = getpass("HF token: ")
```
The token is used to download and load the gated Pyannote model from Hugging Face.

### 4. Load Pyannote
Model used:
`pyannote/speaker-diarization-community-1`

This matches the `diarization_model` default in Lumi's backend config, which is recorded in job metrics for traceability but does not need to match exactly for the service to work — it just needs to be the model your notebook actually loads.

The pipeline should be loaded once at startup and moved to CUDA, not reloaded per request.

### 5. Expose a FastAPI Service
The notebook must serve two routes:
* `POST /diarize`
* `GET /health`

`POST /diarize` — this is the exact contract Lumi's client sends:
* Multipart form field `audio`: the audio file (Lumi sends normalized FLAC)
* Multipart form field `num_speakers` (optional, string): only sent if `DIARIZATION_NUM_SPEAKERS` is set
* Header: `Authorization: Bearer <DIARIZATION_API_KEY>` (only sent if a key is configured)

Expected JSON response:
```json
{
  "segments": [
    { "speaker": "SPEAKER_00", "start": 0.42, "end": 3.11 },
    { "speaker": "SPEAKER_01", "start": 3.11, "end": 7.85 }
  ]
}
```
Each segment must include `speaker`, `start`, and `end`. Segments missing any of these fields are silently dropped by Lumi's client. A response without a `segments` list (or with a non-list value) is treated as invalid and fails the job.

`GET /health` — used for manual verification (see step 10). Any 200 response is sufficient.

TODO: paste the notebook cell that defines and starts this FastAPI app.

### 6. Configure the Shared API Key
The same secret must exist in both environments:
`DIARIZATION_API_KEY=<shared-secret>`

* Colab: read by the FastAPI service to validate the `Authorization` header.
* Lumi: read by `RemoteDiarizationProvider` to set the `Authorization` header on each request.

If the key is empty on the Lumi side, no `Authorization` header is sent at all — the Colab service should reject unauthenticated requests if a key is expected.

### 7. Start the FastAPI Server
TODO: paste the exact notebook cell/command used to start Uvicorn (e.g. host/port, and whether it runs in a background thread inside the notebook).

### 8. Start ngrok
Expose the port the FastAPI service listens on (typically 8000):
`https://<ngrok-domain>`

The ngrok URL changes whenever the Colab runtime or the ngrok tunnel restarts. There is no persistence across sessions unless you're on a paid ngrok plan with a reserved domain.

### 9. Configure Lumi
In Lumi's `.env`:
```env
DIARIZATION_ENABLED=true
DIARIZATION_REMOTE_URL=https://<ngrok-domain>
DIARIZATION_API_KEY=<same-shared-secret>
```
Do not append `/diarize` to `DIARIZATION_REMOTE_URL` — the client appends it automatically (`{DIARIZATION_REMOTE_URL}/diarize`).

Optional:
```env
DIARIZATION_NUM_SPEAKERS=<int>
DIARIZATION_TIMEOUT_SECONDS=1800
```
`DIARIZATION_NUM_SPEAKERS` is only sent to the remote service if set; otherwise Pyannote determines the speaker count automatically. The client-side request timeout defaults to 1800 seconds (30 minutes) to accommodate cold Colab starts and long recordings.

### 10. Verify the Service
Health check:
```bash
curl https://<ngrok-domain>/health
```
Then trigger an actual meeting upload through Lumi and confirm the job reaches the diarization stage successfully (see architecture.md for the full pipeline stage list).

### 11. End-to-End Flow
Upload meeting ↓ Lumi API ↓ ARQ worker ↓ Audio normalization (FLAC) ↓ POST {DIARIZATION_REMOTE_URL}/diarize ↓ Colab T4 ↓ Pyannote Community-1 ↓ Speaker segments (JSON) ↓ Lumi worker ↓ Transcript/speaker alignment ↓ Database

## Troubleshooting

Document only failures you've actually hit — this table should grow from real incidents, not a generic list.

| Symptom | Cause | Fix |
|---|---|---|
| **401 Unauthorized** | `DIARIZATION_API_KEY` mismatch or missing on one side | Confirm the same value is set in both the Colab service and Lumi's `.env` |
| **Connection refused / REMOTE_DIARIZATION_NETWORK_ERROR** | ngrok tunnel or Colab runtime not running | Restart the Colab notebook and ngrok, then update `DIARIZATION_REMOTE_URL` |
| **Diarization stuck / times out** | Colab runtime idle-disconnected mid-job, or audio too long for `DIARIZATION_TIMEOUT_SECONDS` | Re-run the notebook cells; increase the timeout for very long recordings |
| **ngrok URL changed after restart** | Free ngrok tunnels are not persistent | Update `DIARIZATION_REMOTE_URL` in `.env` and restart the worker container |
| **REMOTE_DIARIZATION_INVALID_RESPONSE** | Notebook response is missing the `segments` key or it isn't a list | Check the FastAPI response shape against the contract in step 5 |
| **All speakers labeled the same / one-speaker output** | `DIARIZATION_NUM_SPEAKERS` fixed incorrectly, or genuinely low speaker separation in the audio | Unset `DIARIZATION_NUM_SPEAKERS` to let Pyannote infer speaker count |

TODO: add entries for any notebook-specific failures you've hit (e.g. pipeline is not defined, Uvicorn loop_factory errors, Pyannote TF32 warnings, sample-count mismatches) once confirmed against your actual setup.

This document is the single source of truth for the Colab diarization setup — keep it in sync with the notebook, not the other way around.
