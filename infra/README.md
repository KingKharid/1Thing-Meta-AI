# 1Thing Infrastructure — Modal

Three Modal apps, each deployed independently.

| File | App | What it is |
| :--- | :--- | :--- |
| `modal_worker.py` | `1thing-media-processor` | FFmpeg/Pillow normalization for WhatsApp media |
| `modal_api.py` | `1thing-api` | The FastAPI core as a public ASGI endpoint |
| `modal_web.py` | `1thing-web` | The Next.js standalone server |

## Deploy

```bash
pip install "modal>=1,<2"
modal setup                # one-time browser auth
modal deploy infra/modal_worker.py
modal deploy infra/modal_api.py
modal deploy infra/modal_web.py
```

The API and web apps print their public URLs. Pin CORS to the web origin and
redeploy the API:

```powershell
$env:ONETHING_WEB_ORIGIN="https://<web-app>.modal.run"
modal deploy infra/modal_api.py
```

`modal_web.py` reads `ADMIN_API_KEY` / `SECRET_KEY` from a Modal secret so the
gated `/admin` page can verify the operator key and call the API server-side:

```bash
modal secret create onething-web-admin ADMIN_API_KEY=... SECRET_KEY=...
```

The demo host keeps SQLite on a Modal Volume with `max_containers=1`. That is
durable single-writer storage, not ephemeral disk, but production still belongs
on Postgres (`render.yaml`).

---

## Media worker

`modal_worker.py` is the serverless media pre-processor: WhatsApp voice notes
and photos are normalized here (FFmpeg audio → 16kHz mono WAV, Pillow images
→ compressed JPEG) so the FastAPI service stays small and Meta/Baseten
credits are spent strictly on reasoning, never on byte-shuffling.

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
