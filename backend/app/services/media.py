"""WhatsApp media ingestion: download -> Modal normalize -> Meta extract.

Pipeline for voice notes and photos::

    Graph API download (whatsapp_client.download_media)
      -> MODAL_WORKER_URL normalization (16kHz WAV / compressed JPEG)
      -> Meta /v1/responses with muse-wonder-1.0 -> transcript string,
         fed to the normal text pipeline

Every failure raises :class:`MediaError` with a plain message the webhook
turns into an honest reply. Media must never vanish into silence.
"""

from __future__ import annotations

import base64
import os

import requests

from app.meta_client import segment_image_bytes, transcribe_audio_bytes
from app.services import whatsapp_client


class MediaError(Exception):
    """Anything that stops a voice note or photo becoming text."""


def _worker_url() -> str:
    return (os.getenv("MODAL_WORKER_URL") or "").strip().rstrip("/")


# Formats the Responses API reads without pre-processing. WhatsApp voice
# notes are ogg/opus and always need Modal; a wav or a jpeg can go
# straight through when Modal is not configured.
_DIRECT_AUDIO = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3"}
_DIRECT_IMAGE = {"image/jpeg", "image/png", "image/webp"}
MAX_DIRECT_BYTES = 6 * 1024 * 1024


def _normalize_or_passthrough(
    media_type: str, blob: bytes, mime: str
) -> tuple[bytes, str]:
    """Normalize via Modal, or pass an already-readable file straight on.

    A Modal outage must not silence voice notes that are already in a
    format the model can read. Anything it genuinely cannot read (an ogg
    voice note, an oversized photo) still fails honestly.
    """
    try:
        return normalize_via_modal(media_type, blob)
    except MediaError:
        clean = (mime or "").lower().split(";")[0].strip()
        allowed = _DIRECT_AUDIO if media_type == "audio" else _DIRECT_IMAGE
        if clean in allowed and len(blob) <= MAX_DIRECT_BYTES:
            return blob, clean
        raise


def normalize_via_modal(
    media_type: str, blob: bytes, timeout: int = 90
) -> tuple[bytes, str]:
    """POST raw bytes to the Modal worker; return ``(bytes, mime)``."""
    url = _worker_url()
    if not url:
        raise MediaError("MODAL_WORKER_URL is not configured")
    try:
        res = requests.post(
            url,
            json={
                "media_type": media_type,
                "blob_b64": base64.b64encode(blob).decode(),
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise MediaError(f"Modal worker unreachable: {exc}")
    if res.status_code >= 400:
        raise MediaError(f"Modal worker rejected this file ({res.status_code})")
    try:
        body = res.json()
    except ValueError:
        raise MediaError("Modal worker returned invalid JSON")
    if body.get("status") != "success" or not body.get("blob_b64"):
        raise MediaError("Modal worker could not normalize this file")
    try:
        return base64.b64decode(body["blob_b64"]), body.get("mime", "")
    except Exception:
        raise MediaError("Modal worker returned an unreadable payload")


def ingest_whatsapp_media(media_id: str, media_kind: str) -> str:
    """Turn a WhatsApp voice note or photo into transcript text."""
    if media_kind not in ("audio", "image"):
        raise MediaError(f"unsupported media: {media_kind}")
    fetched = whatsapp_client.download_media(media_id)
    if fetched is None:
        raise MediaError("could not download this file from WhatsApp")
    blob, mime = fetched
    try:
        normalized, out_mime = _normalize_or_passthrough(media_kind, blob, mime)
        if media_kind == "audio":
            return transcribe_audio_bytes(
                normalized,
                filename="voice.wav",
                mime=out_mime or mime or "audio/wav",
            )
        return segment_image_bytes(
            normalized,
            filename="note.jpg",
            mime=out_mime or mime or "image/jpeg",
        )
    except MediaError:
        raise
    except Exception as exc:
        raise MediaError(f"could not read this file ({exc})")
