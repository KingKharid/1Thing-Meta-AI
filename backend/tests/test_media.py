"""Media ingestion tests: WhatsApp download, Modal normalize, Meta extract.

Every network boundary is mocked — the suite proves the wiring (bytes in,
transcript out, honest failure at each hop) without touching Graph, Modal,
or Meta.
"""

import base64

import pytest

import app.main as main
from app.services import media as media_module
from app.services import whatsapp_client
from app.services.media import MediaError, ingest_whatsapp_media, normalize_via_modal


class _Resp:
    def __init__(self, status_code=200, payload=None, content=b""):
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self.text = "boom" if status_code >= 400 else ""

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


@pytest.fixture()
def wa_creds(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "pid")


def test_download_media_returns_bytes_and_mime(monkeypatch, wa_creds):
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        if url.endswith("/MEDIA123"):
            return _Resp(200, {"url": "https://graph.test/blob", "mime_type": "audio/ogg"})
        return _Resp(200, content=b"OGG-BYTES")

    monkeypatch.setattr("requests.get", fake_get)

    assert whatsapp_client.download_media("MEDIA123") == (b"OGG-BYTES", "audio/ogg")
    assert len(calls) == 2
    assert calls[1] == "https://graph.test/blob"


def test_download_media_never_raises(monkeypatch):
    assert whatsapp_client.download_media("") is None
    assert whatsapp_client.download_media("x") is None  # no creds

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "t")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "p")
    monkeypatch.setattr("requests.get", lambda *a, **k: _Resp(404))
    assert whatsapp_client.download_media("x") is None

    def boom(*a, **k):
        import requests as req

        raise req.ConnectionError("down")

    monkeypatch.setattr("requests.get", boom)
    assert whatsapp_client.download_media("x") is None


def test_normalize_via_modal_round_trips_bytes(monkeypatch):
    monkeypatch.setenv("MODAL_WORKER_URL", "https://modal.test/normalize")
    seen = {}

    def fake_post(url, json=None, timeout=None):
        seen.update(json)
        out = base64.b64encode(b"WAV-BYTES").decode()
        return _Resp(200, {"status": "success", "mime": "audio/wav", "blob_b64": out})

    monkeypatch.setattr("requests.post", fake_post)

    blob, mime = normalize_via_modal("audio", b"RAW")
    assert blob == b"WAV-BYTES"
    assert mime == "audio/wav"
    assert seen["media_type"] == "audio"
    assert base64.b64decode(seen["blob_b64"]) == b"RAW"


def test_normalize_via_modal_errors_are_honest(monkeypatch):
    monkeypatch.delenv("MODAL_WORKER_URL", raising=False)
    with pytest.raises(MediaError, match="not configured"):
        normalize_via_modal("audio", b"RAW")

    monkeypatch.setenv("MODAL_WORKER_URL", "https://modal.test/normalize")
    monkeypatch.setattr("requests.post", lambda *a, **k: _Resp(500))
    with pytest.raises(MediaError, match="rejected"):
        normalize_via_modal("audio", b"RAW")

    monkeypatch.setattr("requests.post", lambda *a, **k: _Resp(200, ValueError("nope")))
    with pytest.raises(MediaError, match="invalid JSON"):
        normalize_via_modal("audio", b"RAW")

    monkeypatch.setattr(
        "requests.post", lambda *a, **k: _Resp(200, {"status": "error"})
    )
    with pytest.raises(MediaError, match="could not normalize"):
        normalize_via_modal("audio", b"RAW")


def test_ingest_audio_routes_to_transcribe(monkeypatch):
    monkeypatch.setattr(
        whatsapp_client, "download_media", lambda media_id: (b"OGG", "audio/ogg")
    )
    monkeypatch.setattr(
        media_module, "normalize_via_modal", lambda kind, blob, timeout=90: (b"WAV", "audio/wav")
    )
    monkeypatch.setattr(
        media_module, "transcribe_audio_bytes", lambda data, **k: "buy milk tomorrow"
    )

    assert ingest_whatsapp_media("m1", "audio") == "buy milk tomorrow"


def test_ingest_image_routes_to_segment(monkeypatch):
    monkeypatch.setattr(
        whatsapp_client, "download_media", lambda media_id: (b"JPG", "image/jpeg")
    )
    monkeypatch.setattr(
        media_module, "normalize_via_modal", lambda kind, blob, timeout=90: (b"JPG2", "image/jpeg")
    )
    monkeypatch.setattr(
        media_module, "segment_image_bytes", lambda data, **k: "whiteboard: ship it"
    )

    assert ingest_whatsapp_media("m2", "image") == "whiteboard: ship it"


def test_ingest_rejects_unsupported_and_failures(monkeypatch):
    with pytest.raises(MediaError, match="unsupported"):
        ingest_whatsapp_media("m3", "video")

    monkeypatch.setattr(whatsapp_client, "download_media", lambda media_id: None)
    with pytest.raises(MediaError, match="could not download"):
        ingest_whatsapp_media("m4", "audio")

    monkeypatch.setattr(
        whatsapp_client, "download_media", lambda media_id: (b"x", "audio/ogg")
    )

    def boom(*a, **k):
        raise RuntimeError("worker down")

    monkeypatch.setattr(media_module, "normalize_via_modal", boom)
    with pytest.raises(MediaError, match="worker down"):
        ingest_whatsapp_media("m5", "audio")


def test_transcribe_and_segment_bytes_helpers(monkeypatch):
    from app import meta_client

    monkeypatch.setattr(meta_client.time, "sleep", lambda *_: None)
    seen = {}

    def responses_body(*texts):
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": text} for text in texts
                    ],
                }
            ]
        }

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen["json"] = kwargs.get("json")
        return _Resp(200, responses_body("hello there"))

    monkeypatch.setattr("requests.post", fake_post)

    assert meta_client.transcribe_audio_bytes(b"RIFF") == "hello there"
    assert seen["url"].endswith("/responses")
    content = seen["json"]["input"][0]["content"]
    assert content[0]["type"] == "input_text"
    assert content[1]["type"] == "input_audio"
    assert content[1]["input_audio"]["format"] == "wav"
    assert content[1]["input_audio"]["data"] == base64.b64encode(b"RIFF").decode()

    def image_post(url, **kwargs):
        seen["json"] = kwargs.get("json")
        return _Resp(200, responses_body("board text"))

    monkeypatch.setattr("requests.post", image_post)
    assert meta_client.segment_image_bytes(b"\xff\xd8", mime="image/jpeg") == "board text"
    content = seen["json"]["input"][0]["content"]
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")

    monkeypatch.setattr("requests.post", lambda *a, **k: _Resp(500))
    with pytest.raises(RuntimeError, match="failed"):
        meta_client.transcribe_audio_bytes(b"RIFF")
    with pytest.raises(RuntimeError, match="failed"):
        meta_client.segment_image_bytes(b"\xff\xd8")


def test_media_retries_transient_failures_then_succeeds(monkeypatch):
    from app import meta_client

    monkeypatch.setattr(meta_client.time, "sleep", lambda *_: None)
    attempts = []

    def flaky_post(url, **kwargs):
        attempts.append(1)
        if len(attempts) < 3:
            return _Resp(503)
        return _Resp(
            200,
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "recovered"}],
                    }
                ]
            },
        )

    monkeypatch.setattr("requests.post", flaky_post)

    assert meta_client.transcribe_audio_bytes(b"RIFF") == "recovered"
    assert len(attempts) == 3


def test_media_does_not_retry_a_bad_request(monkeypatch):
    from app import meta_client

    attempts = []

    def bad_request(url, **kwargs):
        attempts.append(1)
        return _Resp(400)

    monkeypatch.setattr("requests.post", bad_request)

    with pytest.raises(RuntimeError, match="400"):
        meta_client.transcribe_audio_bytes(b"RIFF")
    assert len(attempts) == 1


def test_audio_format_is_derived_from_mime_and_filename():
    from app import meta_client

    assert meta_client._audio_format("audio/ogg; codecs=opus", "x.ogg") == "ogg"
    assert meta_client._audio_format("", "note.mp3") == "mp3"
    assert meta_client._audio_format("", "") == "wav"


def test_ingest_falls_back_to_direct_bytes_when_modal_is_unconfigured(monkeypatch):
    monkeypatch.delenv("MODAL_WORKER_URL", raising=False)
    monkeypatch.setattr(
        whatsapp_client, "download_media", lambda media_id: (b"RIFF", "audio/wav")
    )
    monkeypatch.setattr(
        media_module, "transcribe_audio_bytes", lambda data, **k: "already a wav"
    )

    assert ingest_whatsapp_media("m6", "audio") == "already a wav"


def test_ingest_still_fails_honestly_for_an_ogg_without_modal(monkeypatch):
    monkeypatch.delenv("MODAL_WORKER_URL", raising=False)
    monkeypatch.setattr(
        whatsapp_client, "download_media", lambda media_id: (b"OGG", "audio/ogg")
    )

    with pytest.raises(MediaError, match="MODAL_WORKER_URL"):
        ingest_whatsapp_media("m7", "audio")



def test_handle_media_pipes_transcript_into_pipeline(monkeypatch):
    seen = {}

    def fake_ingest(media_id, kind):
        seen["ingest"] = (media_id, kind)
        return "buy milk tomorrow"

    def fake_pipeline(text, user_id="unknown"):
        seen["pipeline"] = (text, user_id)
        return {"selected_task": {"title": "t"}}

    monkeypatch.setattr(main, "ingest_whatsapp_media", fake_ingest)
    monkeypatch.setattr(main, "handle_pipeline", fake_pipeline)

    result = main.handle_media("audio", "+15550007777", "MEDIA9")

    assert seen["ingest"] == ("MEDIA9", "audio")
    assert seen["pipeline"] == ("buy milk tomorrow", "+15550007777")
    assert result == {"selected_task": {"title": "t"}}


def test_handle_media_failure_sends_honest_reply(monkeypatch):
    sent = []
    monkeypatch.setattr(
        main, "ingest_whatsapp_media", lambda *a, **k: (_ for _ in ()).throw(MediaError("nope"))
    )
    monkeypatch.setattr(main, "_deliver", lambda user_id, body: sent.append((user_id, body)))

    assert main.handle_media("audio", "+15550007777", "MEDIA9") == {}
    assert len(sent) == 1


def test_handle_media_unsupported_kind_never_ingests(monkeypatch):
    sent = []
    monkeypatch.setattr(
        main,
        "ingest_whatsapp_media",
        lambda *a, **k: pytest.fail("video must not reach ingestion"),
    )
    monkeypatch.setattr(main, "_deliver", lambda user_id, body: sent.append((user_id, body)))

    assert main.handle_media("video", "+15550007777", "MEDIA9") == {}
    assert len(sent) == 1
    assert "video" in sent[0][1]
