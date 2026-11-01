import base64
import os
import json
import time

import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Meta Model API Credentials ($150 Credits)
META_API_KEY = os.getenv("MODEL_API_KEY")
META_BASE_URL = os.getenv("META_API_BASE_URL", "https://api.meta.ai/v1")
META_HEADERS = {"Authorization": f"Bearer {META_API_KEY}"}

# Baseten Open-Weight Inference ($100 Credits + 2M TPM)
BASETEN_API_KEY = os.getenv("BASETEN_API_KEY")
BASETEN_BASE_URL = os.getenv("BASETEN_BASE_URL", "https://inference.baseten.co/v1")
BASETEN_MODEL = os.getenv("BASETEN_MODEL", "meta-models/muse-spark-open-1026")

# A capture surface waits on this call, so it must never hang. The
# OpenAI SDK defaults to ten minutes, which would look like a dead app.
REQUEST_TIMEOUT = float(os.getenv("MODEL_TIMEOUT_SECONDS", "20"))

baseten_client = (
    OpenAI(base_url=BASETEN_BASE_URL, api_key=BASETEN_API_KEY, timeout=REQUEST_TIMEOUT)
    if BASETEN_API_KEY
    else None
)

# Media runs through the Responses API. The OpenAI-compatible
# /audio/transcriptions and /media/segmentation routes return 404 on the
# Meta Model API; /responses with an input_audio or input_image part is
# the route that actually answers. Verified against the live endpoint:
# a synthesized voice note transcribes and a photographed note reads back
# its lines. muse-voice-transcribe-1.0 is listed by GET /models but is not
# routable on /responses, so the multimodal model does the listening.
META_RESPONSES_URL = f"{META_BASE_URL.rstrip('/')}/responses"
META_VOICE_MODEL = os.getenv("META_VOICE_MODEL", "muse-wonder-1.0")
META_VISION_MODEL = os.getenv("META_VISION_MODEL", "muse-wonder-1.0")

# A voice note or photo is bigger and slower than a text turn.
MEDIA_TIMEOUT = float(os.getenv("MEDIA_TIMEOUT_SECONDS", "90"))

TRANSCRIBE_PROMPT = (
    "Transcribe this voice note verbatim, in the speaker's own words. "
    "Output only the transcript: no commentary, no labels, no summary, "
    "no bullet points. Keep the speaker's phrasing. If there is no speech, "
    "output nothing at all."
)

EXTRACT_IMAGE_PROMPT = (
    "Read this photo as a capture surface. Extract every task, commitment, "
    "or loose end written in it, one per line, in the author's own words. "
    "Output only those lines. Do not add work that is not written there. "
    "If the photo contains no task text, output nothing at all."
)

# Transient upstream failures are worth one retry; a bad request is not.
_RETRY_STATUS = {429, 500, 502, 503, 504}


def _post_with_retry(url: str, *, timeout: float, **kwargs) -> requests.Response:
    """POST with bounded retries on 429/5xx and network errors."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            res = requests.post(url, timeout=timeout, **kwargs)
        except requests.RequestException as exc:
            last_error = exc
        else:
            if res.status_code not in _RETRY_STATUS or attempt == 2:
                return res
        time.sleep(0.5 * (2**attempt))
    raise RuntimeError(f"request failed after retries: {last_error}")


def _response_text(body: dict) -> str:
    """Pull the assistant's text out of a Responses API payload."""
    chunks: list[str] = []
    for item in body.get("output") or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if part.get("type") == "output_text":
                chunks.append(part.get("text") or "")
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _media_request(model: str, content: list[dict], timeout: float) -> str:
    if not META_API_KEY:
        raise RuntimeError("MODEL_API_KEY is not configured")
    res = _post_with_retry(
        META_RESPONSES_URL,
        timeout=timeout,
        headers={**META_HEADERS, "Content-Type": "application/json"},
        json={"model": model, "input": [{"role": "user", "content": content}]},
    )
    if res.status_code != 200:
        raise RuntimeError(f"{model} failed: {res.status_code} - {res.text}")
    return _response_text(res.json())


# The Responses API names audio formats without the mime prefix.
_AUDIO_FORMATS = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/ogg": "ogg",
    "audio/webm": "webm",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/flac": "flac",
}


def _audio_format(mime: str, filename: str) -> str:
    fmt = _AUDIO_FORMATS.get((mime or "").lower().split(";")[0].strip())
    if fmt:
        return fmt
    suffix = os.path.splitext(filename or "")[1].lower().lstrip(".")
    return suffix or "wav"


def transcribe_audio_dump(file_path: str) -> str:
    """Transcribe an audio file through the Meta Responses API."""
    with open(file_path, "rb") as f:
        return transcribe_audio_bytes(
            f.read(), filename=os.path.basename(file_path), mime="audio/wav"
        )


def segment_visual_note(image_path: str) -> str:
    """Read the task text out of a photographed note."""
    with open(image_path, "rb") as f:
        return segment_image_bytes(
            f.read(), filename=os.path.basename(image_path), mime="image/jpeg"
        )


def transcribe_audio_bytes(
    data: bytes, filename: str = "voice.wav", mime: str = "audio/wav"
) -> str:
    """Transcribe in-memory audio through the Meta Responses API."""
    content = [
        {"type": "input_text", "text": TRANSCRIBE_PROMPT},
        {
            "type": "input_audio",
            "input_audio": {
                "data": base64.b64encode(data).decode(),
                "format": _audio_format(mime, filename),
            },
        },
    ]
    return _media_request(META_VOICE_MODEL, content, MEDIA_TIMEOUT)


def segment_image_bytes(
    data: bytes, filename: str = "note.jpg", mime: str = "image/jpeg"
) -> str:
    """Read the task text out of an in-memory photo."""
    kind = (mime or "image/jpeg").split(";")[0].strip()
    content = [
        {"type": "input_text", "text": EXTRACT_IMAGE_PROMPT},
        {
            "type": "input_image",
            "image_url": f"data:{kind};base64,{base64.b64encode(data).decode()}",
        },
    ]
    return _media_request(META_VISION_MODEL, content, MEDIA_TIMEOUT)


SYSTEM_PROMPT = """
You are the executive-function core of 1Thing. Your objective is to eliminate decision paralysis and ADHD overwhelm.
You receive a raw, unstructured thought dump — possibly one line, possibly a week of loose ends — plus the user's context (available minutes, energy level, time of day).

RULES:
1. Extract every distinct task, commitment, or loose end in the dump. One entry per thing to do. Ignore pure feeling unless it implies an action.
2. Never invent work that is not in the dump. A one-line dump returns exactly one task.
3. For each task write the exact micro-action for the first two minutes — a physical step someone can start right now. Never restate the title.
4. Estimate minutes and energy honestly for each task.
5. Order the array by what should happen first for THIS user right now, given available_minutes, energy, and time_of_day. The first entry is what the user sees on their wrist and phone.
6. Return strictly valid JSON matching this schema:
{
  "tasks": [
    {
      "title": "Short action title",
      "first_micro_step": "Exact physical action for the first 2 minutes",
      "estimated_minutes": 15,
      "energy_required": "low|medium|high",
      "reasoning": "Why this one now"
    }
  ]
}
"""

def evaluate_single_task_meta(raw_dump: str, user_context: dict) -> dict:
    """Calls Muse Spark 1.3 via Meta Model API."""
    url = f"{META_BASE_URL}/chat/completions"
    payload = {
        "model": "muse-spark-1.3",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"User Context: {json.dumps(user_context)}\n\nThought Dump: {raw_dump}"}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    res = requests.post(url, headers={**META_HEADERS, "Content-Type": "application/json"}, json=payload, timeout=REQUEST_TIMEOUT)
    if res.status_code == 200:
        return json.loads(res.json()["choices"][0]["message"]["content"])
    raise Exception(f"Muse Spark failed: {res.status_code} - {res.text}")

def evaluate_single_task_baseten(raw_dump: str, user_context: dict) -> dict:
    """Calls Muse Spark Open on Baseten (Qualifies for $10K Open-Weights Bonus)."""
    if baseten_client is None:
        raise RuntimeError("BASETEN_API_KEY is not configured")
    response = baseten_client.chat.completions.create(
        model=BASETEN_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"User Context: {json.dumps(user_context)}\n\nThought Dump: {raw_dump}"}
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        timeout=REQUEST_TIMEOUT,
    )
    return json.loads(response.choices[0].message.content)
