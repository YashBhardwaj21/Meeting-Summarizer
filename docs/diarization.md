# Diarization Service

Lumi uses Pyannote Community-1 for speaker diarization.

Pyannote does not run inside the main Docker Compose stack. Instead, Lumi's ARQ worker sends normalized meeting audio to a separate HTTP service. For the current setup, that service runs in Google Colab on a Tesla T4 GPU and is exposed through ngrok.

```text
Lumi Worker
    │
    │ HTTPS + Bearer token
    ▼
ngrok public URL
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
    │
    ▼
Transcript / speaker alignment
```

## Credentials vs. session state

These are two different categories of problem when something breaks, so keep them separate:

```text
Permanent credentials (survive a Colab restart):
  HF_TOKEN
  DIARIZATION_API_KEY
  ngrok auth token

Per-session state (lost on every Colab restart):
  FastAPI process
  Pyannote pipeline in RAM
  ngrok tunnel
  DIARIZATION_REMOTE_URL (the ngrok URL itself)
```

If diarization suddenly stops working, check session state first — it's the more common failure and it resets every time the Colab runtime disconnects.

## Requirements

- Google Colab with a T4 GPU
- Hugging Face account and access token
- ngrok account and auth token
- Lumi running locally via Docker Compose

## 1. Start a T4 Colab runtime

`Runtime → Change runtime type → T4 GPU`

```python
import torch

print("Torch:", torch.__version__)
print("CUDA:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
```

Expected:

```text
CUDA: True
GPU: Tesla T4
```

Don't continue on a CPU runtime — `pipeline.to(torch.device("cuda"))` later will raise `AssertionError: Torch not compiled with CUDA enabled` if CUDA isn't available.

## 2. Install dependencies

```python
!pip install -q pyannote.audio fastapi uvicorn python-multipart pyngrok
```

Colab's default NumPy version has caused binary-compatibility errors with Pyannote's compiled dependencies. Pin it:

```python
!pip uninstall -y numpy
!pip install --no-cache-dir numpy==2.2.6
```

Verify:

```python
import torch
import torchaudio
import pyannote.audio

print("Torch:", torch.__version__)
print("Torchaudio:", torchaudio.__version__)
print("Pyannote:", pyannote.audio.__version__)
print("CUDA:", torch.cuda.is_available())
```

```python
!ffmpeg -version
```

FFmpeg needs to be present — the `/diarize` endpoint shells out to it (see step 6).

## 3. Configure the Hugging Face token

```python
import os
from getpass import getpass

os.environ["HF_TOKEN"] = getpass("HF token: ")
```

The token is used to load the gated Pyannote model. Store it in Colab Secrets for repeat use instead of retyping it each session.

## 4. Configure the shared diarization API key

Generate one strong secret and reuse it across sessions — this is a permanent credential.

```python
import os
from getpass import getpass

os.environ["DIARIZATION_API_KEY"] = getpass("Diarization API key: ")

print("DIARIZATION_API_KEY configured:", bool(os.environ["DIARIZATION_API_KEY"]))
```

Use the same value in Lumi's `.env`:

```env
DIARIZATION_API_KEY=<same-secret>
```

## 5. Load Pyannote

```python
from pyannote.audio import Pipeline
import torch

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token=os.environ["HF_TOKEN"],
)

pipeline.to(torch.device("cuda"))

print("Pyannote loaded on:", torch.cuda.get_device_name(0))
```

Load once, before starting the server. Reloading it per request would make every diarization request pay the model-load cost.

## 6. Define the FastAPI service

```python
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
import tempfile
import os
import subprocess

app = FastAPI(title="Lumi Diarization Server")
```

```python
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "cuda": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0),
        "model": "pyannote/speaker-diarization-community-1",
    }
```

```python
@app.post("/diarize")
async def diarize(
    audio: UploadFile = File(...),
    num_speakers: int | None = Form(None),
    authorization: str | None = Header(None),
):
    expected_key = f"Bearer {os.environ['DIARIZATION_API_KEY']}"

    if authorization != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    input_path = None
    wav_path = None

    try:
        # Save uploaded file temporarily.
        suffix = os.path.splitext(audio.filename or "")[1] or ".input"

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as tmp:
            input_path = tmp.name

            while True:
                chunk = await audio.read(1024 * 1024)

                if not chunk:
                    break

                tmp.write(chunk)

        # Convert input to deterministic audio format:
        # mono, 16 kHz, PCM 16-bit WAV.
        wav_path = input_path + ".wav"

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                wav_path,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Run diarization.
        kwargs = {}

        if num_speakers is not None:
            kwargs["num_speakers"] = num_speakers

        output = pipeline(
            wav_path,
            **kwargs,
        )

        diarization = output.exclusive_speaker_diarization

        segments = []

        for turn, _, speaker in diarization.itertracks(
            yield_label=True
        ):
            duration = turn.end - turn.start

            # Ignore extremely small diarization artifacts.
            if duration < 0.10:
                continue

            segments.append(
                {
                    "speaker": speaker,
                    "start": float(turn.start),
                    "end": float(turn.end),
                }
            )

        return {
            "segments": segments,
            "num_segments": len(segments),
        }

    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to convert uploaded audio with FFmpeg.",
        ) from exc

    finally:
        if input_path and os.path.exists(input_path):
            os.remove(input_path)

        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)
```

This is the actual contract Lumi's worker relies on — matches `backend/app/integrations/diarization/remote.py`:

| Part | Detail |
|---|---|
| Method / path | `POST {DIARIZATION_REMOTE_URL}/diarize` |
| Auth | `Authorization: Bearer <DIARIZATION_API_KEY>` header, sent only if a key is configured on the Lumi side |
| Body | Multipart form. Field `audio`: the file (Lumi sends normalized FLAC). Field `num_speakers` (optional, string): sent only if `DIARIZATION_NUM_SPEAKERS` is set in Lumi's `.env` |
| Server-side conversion | The endpoint re-encodes whatever it receives to mono, 16 kHz, PCM 16-bit WAV via `ffmpeg` before running Pyannote — the incoming format doesn't need to match Pyannote's expected input exactly |
| Response | `{"segments": [{"speaker": str, "start": float, "end": float}, ...], "num_segments": int}` |
| Filtering | Segments shorter than 0.10s are dropped server-side. Lumi's own alignment step (`align_speakers`) applies the same 0.10s filter again on receipt — redundant but harmless |
| Client parsing | Lumi only reads the `segments` list; `num_segments` and any other extra fields are ignored. Segments missing `speaker`, `start`, or `end` are silently skipped. A response where `segments` isn't a list fails the job |

Temp files (the raw upload and the converted WAV) are cleaned up after each request regardless of success or failure.

## 7. Start Uvicorn

```python
import threading
import uvicorn

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

threading.Thread(target=run_server, daemon=True).start()
```

## 8. Verify locally

```python
import requests

r = requests.get("http://127.0.0.1:8000/health")
print(r.status_code)
print(r.json())
```

Expected: `200` and a body confirming `cuda: true` and the GPU name. Don't move on to ngrok until this succeeds.

## 9. Expose via ngrok

```python
from pyngrok import ngrok
from getpass import getpass

ngrok_token = getpass("ngrok token: ")
ngrok.set_auth_token(ngrok_token)
```

```python
public_url = ngrok.connect(8000).public_url
print(public_url)
```

```text
https://<random-subdomain>.ngrok-free.dev
```

Test the public endpoint:

```python
public_health = requests.get(f"{public_url}/health")
print(public_health.status_code)
print(public_health.json())
```

If this raises `NameError: name 'requests' is not defined`, it means this cell ran in a session where step 8's `import requests` never executed — usually after a runtime restart or running cells out of order. Re-run the `import requests` line (or just re-run step 8) before retrying.

Free ngrok URLs are session-specific — a Colab or tunnel restart issues a new one.

## 10. Configure Lumi

```env
DIARIZATION_ENABLED=true
DIARIZATION_REMOTE_URL=https://<ngrok-domain>
DIARIZATION_API_KEY=<same-secret>
```

Do not append `/diarize` — Lumi's client appends it automatically:

```env
# Correct
DIARIZATION_REMOTE_URL=https://example.ngrok-free.dev

# Incorrect
DIARIZATION_REMOTE_URL=https://example.ngrok-free.dev/diarize
```

Optional:

```env
DIARIZATION_NUM_SPEAKERS=2
DIARIZATION_TIMEOUT_SECONDS=1800
```

Leave `DIARIZATION_NUM_SPEAKERS` unset unless you know the exact speaker count for the recording — Pyannote's automatic inference is generally more reliable than a guessed value. `DIARIZATION_TIMEOUT_SECONDS` defaults to 1800s to tolerate long recordings and a cold Colab start.

## 11. Restart the Lumi worker

```bash
docker compose up -d backend worker
```

Or, for a full rebuild:

```bash
docker compose up --build
```

## 12. End-to-end test

Don't test by uploading a file straight to the Colab endpoint — test through Lumi itself, so you're validating the real path:

```text
User uploads meeting → Lumi API → ARQ worker → audio normalization
  → POST /diarize → ngrok → Colab T4 → Pyannote
  → JSON speaker segments → Lumi worker
  → speaker/transcript alignment → database → frontend
```

## Restarting after a Colab disconnect

A runtime restart clears the process — FastAPI, the loaded pipeline, and the ngrok tunnel are all gone.

1. Reconnect to the T4 runtime.
2. Re-run the dependency/setup cells.
3. Restore `HF_TOKEN`.
4. Restore `DIARIZATION_API_KEY`.
5. Reload the Pyannote pipeline.
6. Restart FastAPI (Uvicorn thread).
7. Verify `/health` locally.
8. Start ngrok.
9. Verify the public `/health`.
10. If the ngrok URL changed, update `DIARIZATION_REMOTE_URL` in Lumi's `.env`.
11. Restart the Lumi worker.

`DIARIZATION_API_KEY` does not need to change across restarts — only the ngrok URL does.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | `DIARIZATION_API_KEY` differs between Colab and Lumi | Use the exact same value in both `.env` and the Colab session |
| `ERR_NGROK_3200` / 404 from ngrok | Colab runtime or tunnel is offline | Restart FastAPI and ngrok, update `DIARIZATION_REMOTE_URL` with the new URL |
| `Connection refused` | FastAPI isn't listening on port 8000 | Re-run the Uvicorn startup cell, confirm `http://127.0.0.1:8000/health` responds |
| `pipeline is not defined` | Runtime restarted; the pipeline variable no longer exists | Re-run the pipeline-load cell before starting the server again |
| `KeyError: 'DIARIZATION_API_KEY'` | Env var was lost after a restart | Re-run the credential cell before starting FastAPI |
| `AssertionError: Torch not compiled with CUDA enabled` | Runtime type isn't set to T4 GPU, or GPU wasn't actually allocated | `Runtime → Change runtime type → T4 GPU`, then re-run from the top |
| `NameError: name 'requests' is not defined` on the public health check | `import requests` didn't run in the current session (cells run out of order or after a restart) | Re-run the local-health-check cell (step 8) first |
| NumPy import/binary error | Incompatible NumPy version pulled in by another package | Re-run the NumPy pin cell (`numpy==2.2.6`), restart the runtime if prompted |
| One speaker for the whole recording | Fixed `DIARIZATION_NUM_SPEAKERS`, or the recording genuinely has low speaker separation | Unset `DIARIZATION_NUM_SPEAKERS` and let Pyannote infer the count |

## Scope of the Notebook

The notebook's only job is to bring the diarization service online: install dependencies, load credentials, load the Pyannote pipeline, start the FastAPI server, and verify connectivity through ngrok. It is infrastructure, not application logic.

Keep it that way:

- No hardcoded meeting audio, test fixtures, or references to specific Lumi meetings.
- No duplicated business logic — the `/health` and `/diarize` handlers shown above are the full extent of what it should implement.
- No copies of Lumi's request/response contract as comments or docstrings that could drift out of sync.

The contract itself — request shape, auth header, response fields — is defined once, in code, here:

```text
backend/app/integrations/diarization/remote.py
```

If that file changes (a new field, a different auth scheme, a different audio format), update both the notebook's `/diarize` handler and this document to match. Treat `remote.py` as the source of truth; the notebook and this page are downstream of it, not the other way around.
