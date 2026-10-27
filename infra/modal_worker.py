import modal

app = modal.App("1thing-media-processor")
image = modal.Image.debian_slim().pip_install("requests", "ffmpeg-python", "fastapi[standard]")

@app.function(image=image, timeout=60)
@modal.fastapi_endpoint(method="POST")
def process_incoming_media(payload: dict):
    """
    Serverless media pre-processing worker running on Modal infrastructure.
    """
    media_type = payload.get("media_type")
    return {
        "status": "success",
        "worker": "Modal Serverless Worker",
        "media_type": media_type,
        "normalized_ready": True
    }