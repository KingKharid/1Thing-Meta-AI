"""Deploy the 1Thing FastAPI core to Modal as a public ASGI endpoint.

This is the *demo* host: one container, one durable Modal Volume holding
the SQLite file. It exists so a judge can click a URL today. The
production path is ``Dockerfile`` + ``render.yaml`` with managed
PostgreSQL 16, and this module does not change that.

Two constraints make the volume safe here:

- ``max_containers=1`` — exactly one process owns the SQLite file, so
  there is no multi-writer race.
- ``min_containers=0`` with a 10-minute scale-down — warm during judging,
  scaled to zero (and free) the rest of the time.

Deploy::

    modal deploy infra/modal_api.py

Then set ``ONETHING_WEB_ORIGIN`` to the deployed web origin and redeploy
so CORS names the real origin instead of falling back to ``*``.
"""

from __future__ import annotations

import os

import modal
from dotenv import dotenv_values

APP_NAME = "1thing-api"
VOLUME_NAME = "onething-data"

# The deploy runs locally, so the repo's own .env is the source of truth.
_env = dotenv_values(r"E:\1Thing-Meta-AI\.env")

# Demo overrides. Everything else (model keys, WhatsApp token, admin key)
# comes straight from .env and is never written into this file.
_env.update(
    {
        # A Modal Volume is durable storage, not the ephemeral disk that
        # made the original SQLite deployment a liability.
        "DATABASE_URL": "sqlite:////data/onething.db",
        "RUN_SCHEDULER": "1",
        "ALLOWED_ORIGINS": os.getenv("ONETHING_WEB_ORIGIN", "*"),
    }
)

secret = modal.Secret.from_dict({k: v for k, v in _env.items() if v})

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("backend/requirements.txt")
    .env({"PYTHONPATH": "/root"})
    # Must be last: Modal ships local files at container start, not at build.
    .add_local_dir("backend/app", remote_path="/root/app")
)

volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

app = modal.App(APP_NAME)


@app.function(
    image=image,
    secrets=[secret],
    volumes={"/data": volume},
    min_containers=0,
    max_containers=1,
    scaledown_window=600,
    timeout=900,
)
@modal.asgi_app()
def api():
    from app.main import app as fastapi_app

    return fastapi_app
