import os
import json
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

def transcribe_audio_dump(file_path: str) -> str:
    """Calls Meta Muse Voice Transcribe API."""
    url = f"{META_BASE_URL}/audio/transcriptions"
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {"model": "muse-voice-transcribe-1.0"}
        res = requests.post(url, headers=META_HEADERS, files=files, data=data, timeout=REQUEST_TIMEOUT)
    if res.status_code == 200:
        return res.json().get("text", "")
    raise Exception(f"Muse Voice Transcribe failed: {res.status_code} - {res.text}")

def segment_visual_note(image_path: str) -> str:
    """Calls SAM 3.1 & Muse Image for visual text segmentation."""
    url = f"{META_BASE_URL}/media/segmentation"
    with open(image_path, "rb") as f:
        files = {"image": f}
        data = {"model": "sam-3.1"}
        res = requests.post(url, headers=META_HEADERS, files=files, data=data, timeout=REQUEST_TIMEOUT)
    if res.status_code == 200:
        return res.json().get("extracted_text", "")
    raise Exception(f"SAM 3.1 Segmentation failed: {res.status_code} - {res.text}")

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
