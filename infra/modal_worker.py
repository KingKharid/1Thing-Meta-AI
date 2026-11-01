"""1Thing serverless media pre-processor (Modal).

WHY MODAL: audio normalization (FFmpeg) and image compression are CPU-heavy
and bursty. Running them on Modal keeps the FastAPI service small and
preserves Meta/Baseten inference credits strictly for reasoning.

Data flow (see ``backend/app/services/media.py`` for the caller)::

    WhatsApp voice note / photo
      -> backend downloads raw bytes via Graph API
      -> POSTs them here
      -> this worker returns normalized bytes
      -> backend feeds them to Meta /v1/responses (muse-wonder-1.0)

Deploy once with::

    modal setup && modal deploy infra/modal_worker.py

then set ``MODAL_WORKER_URL`` to the printed https endpoint.
"""

import base64
import io
import subprocess
import tempfile
from pathlib import Path

import modal

app = modal.App("1thing-media-processor")
image = (
    modal.Image.debian_slim()
    .apt_install("ffmpeg")
    .pip_install("pillow", "fastapi[standard]")
)

# WhatsApp voice notes and photos top out well below this; anything
# bigger is rejected before it can burn worker minutes.
MAX_BLOB_BYTES = 12 * 1024 * 1024


def _normalize_audio(raw: bytes) -> tuple[bytes, str]:
    """FFmpeg: any audio container -> 16kHz mono WAV for the transcriber."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in"
        dst = Path(tmp) / "out.wav"
        src.write_bytes(raw)
        proc = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(src),
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(dst),
            ],
            capture_output=True,
            timeout=50,
        )
        if proc.returncode != 0 or not dst.exists():
            detail = proc.stderr.decode(errors="replace")[:300]
            raise ValueError(f"ffmpeg could not decode this audio ({detail})")
        return dst.read_bytes(), "audio/wav"


def _normalize_image(raw: bytes) -> tuple[bytes, str]:
    """Pillow: any image -> max-1568px JPEG for the vision segmenter."""
    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(raw)) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((1568, 1568))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=70, optimize=True)
            return buf.getvalue(), "image/jpeg"
    except Exception as exc:
        raise ValueError(f"pillow could not decode this image ({exc})")


@app.function(image=image, timeout=120)
@modal.fastapi_endpoint(method="POST")
def process_incoming_media(payload: dict):
    """Normalize one media blob.

    Request: ``{"media_type": "audio"|"image", "blob_b64": str}``.
    Response: ``{"status": "success", "mime": str, "bytes": int,
    "blob_b64": str}``. Bad input answers 400/422 with a plain detail
    string the backend surfaces honestly.
    """
    from fastapi import HTTPException

    payload = payload or {}
    media_type = payload.get("media_type")
    if media_type not in ("audio", "image"):
        raise HTTPException(
            status_code=400, detail="media_type must be 'audio' or 'image'"
        )
    try:
        raw = base64.b64decode(payload.get("blob_b64", ""), validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="blob_b64 is not valid base64")
    if not raw:
        raise HTTPException(status_code=400, detail="blob_b64 decoded to empty bytes")
    if len(raw) > MAX_BLOB_BYTES:
        raise HTTPException(status_code=400, detail="blob exceeds the 12MB budget")

    try:
        if media_type == "audio":
            out, mime = _normalize_audio(raw)
        else:
            out, mime = _normalize_image(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "status": "success",
        "worker": "Modal Serverless Worker",
        "media_type": media_type,
        "mime": mime,
        "bytes": len(out),
        "blob_b64": base64.b64encode(out).decode(),
    }
