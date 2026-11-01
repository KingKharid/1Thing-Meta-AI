"""Serve the 1Thing web sanctuary from Modal.

The judge-facing URL. It runs the Next.js standalone server, built at
image-build time with ``NEXT_PUBLIC_API_URL`` pointing at the deployed
Modal API.

Deploy::

    modal deploy infra/modal_web.py

The API's ``ALLOWED_ORIGINS`` must then name this app's origin.
"""

from __future__ import annotations

import modal

APP_NAME = "1thing-web"
API_URL = "https://kingkharid--1thing-api-api.us-east.modal.run"
WEB_ORIGIN = "https://kingkharid--1thing-web-web.us-east.modal.run"

# Server-side only, stored in Modal rather than in this file:
#   modal secret create onething-web-admin ADMIN_API_KEY=... SECRET_KEY=...
# The /admin page uses them to mint its session cookie and to call the API
# with X-Admin-Key. Neither ever reaches the browser.
ADMIN_SECRET_NAME = "onething-web-admin"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .run_commands(
        "apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg",
        "curl -fsSL https://deb.nodesource.com/setup_22.x | bash -",
        "apt-get install -y nodejs",
    )
    .env(
        {
            # Baked at build time: the browser and the server both need it.
            "NEXT_PUBLIC_API_URL": API_URL,
            "NEXT_PUBLIC_PHONE_NUMBER": "+15550007777",
            "NEXT_TELEMETRY_DISABLED": "1",
        }
    )
    # copy=True because npm needs the sources during the build. Secrets and
    # local build output stay out of the image.
    .add_local_dir(
        "web",
        remote_path="/web",
        copy=True,
        ignore=["node_modules", ".next", ".env.local", "*.log", "*.tsbuildinfo"],
    )
    .run_commands(
        "cd /web && npm ci",
        "cd /web && npm run build",
        # Standalone output ships without static assets; copy them in.
        "cp -r /web/.next/static /web/.next/standalone/.next/static",
    )
)

app = modal.App(APP_NAME)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name(ADMIN_SECRET_NAME)],
    min_containers=0,
    max_containers=2,
    scaledown_window=600,
    timeout=900,
)
@modal.web_server(port=3000, startup_timeout=180)
def web():
    import os
    import subprocess

    # Merge the container environment: ADMIN_API_KEY and SECRET_KEY arrive
    # through the Modal secret and must survive into the Next server.
    subprocess.Popen(
        ["node", "server.js"],
        cwd="/web/.next/standalone",
        env={
            **os.environ,
            "PORT": "3000",
            "HOSTNAME": "0.0.0.0",
            "NODE_ENV": "production",
            "NEXT_PUBLIC_API_URL": API_URL,
            "NEXT_PUBLIC_PHONE_NUMBER": "+15550007777",
        },
    )
