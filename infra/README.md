# 1Thing Infrastructure — Modal Media Worker

`modal_worker.py` is the serverless media pre-processor: WhatsApp voice notes
and photos are normalized here (FFmpeg audio → 16kHz mono WAV, Pillow images
→ compressed JPEG) so the FastAPI service stays small and Meta/Baseten
credits are spent strictly on reasoning, never on byte-shuffling.

## Deploy

```bash
pip install modal
modal setup                # one-time browser auth, picks the $30/mo free tier
modal deploy infra/modal_worker.py
```

Copy the printed `https://…modal.run` endpoint into the backend env:

```bash
MODAL_WORKER_URL=https://<your-app>--process-incoming-media.modal.run
```

The backend reads it at call time (`services/media.py`) — no restart needed
after the first deploy, just set it before voice notes arrive.

## Contract

Request `POST {media_type: "audio"|"image", blob_b64: str}` (12MB cap).
Response `{status: "success", mime, bytes, blob_b64}` or a 400/422 with a
plain detail string the webhook turns into an honest reply.

## Local development without Modal

Leave `MODAL_WORKER_URL` unset: the media path raises a clear `MediaError`
("not configured") and the sender gets the honest fallback reply instead of
silence. Text dumps are unaffected — they never touch this worker.
