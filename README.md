# 1Thing — One Physical Next Step

> **Meta Global AI Developer Hackathon — Indie Developer track.**
> Repo: [KingKharid/1Thing-Meta-AI](https://github.com/KingKharid/1Thing-Meta-AI)
> **Demo: <https://kingkharid--1thing-web-web.us-east.modal.run/demo>**
> Video: `<!-- TODO: replace with the submission video -->`

Every productivity app shows you the mountain. 1Thing refuses.

You dump a week of chaos into one message — typed, spoken, or photographed.
The model reads all of it, files every distinct task into a hidden reserve, and
puts **exactly one physical next step** on screen. Press DONE and the next one
appears, in the order the model chose. You never see the list.

**Core invariant:** *"Never show the mountain. One physical next step."*

---

## Try it

1. Open the demo link above and press **WATCH A WEEK BECOME ONE**.
2. The composer arrives preloaded with a messy ten-line dump. Press **SEND**.
3. Nine things are filed, one is shown. Press **DONE** — the next one appears.

There is no sign-up and no task list. `/demo` resets only the demo identity.

---

## How the model decides

`backend/app/services/triage.py` is the only place that asks a model for an
order. A dump is not a task, so `extract()` returns **every** distinct thing it
finds, ordered by what this person should do first given the hour, their
available minutes, and their energy:

```text
"ok so this week is a mess…"          ┌─ 1. Call dentist about painful crown   ← shown
  + 9 more loose ends        ────────▶│  2. Send overdue venue deposit          ┐
                                      │  3. Order Mom's birthday gift           │ 8 more,
                                      │  …                                      ┘ hidden
                                      └─ filed in the model's order, never listed
```

- Extraction is ordered, de-duplicated, and capped at 20 tasks per dump.
- Every task is persisted; only the head is activated.
- A dump **never yanks** a task you are already mid-step on. The new head waits
  in reserve behind it (Invariant 1).
- If both providers fail, a verbatim heuristic files your own words rather than
  losing the week. `step_source` tells the surface which of the three wrote the
  step: `user`, `engine`, `heuristic`, or `none`.

**Provider order** (`PRIMARY_ENGINE`, default `baseten`):

1. `meta-models/muse-spark-open-1026` on Baseten — open weights, and the
   open-weights prize track.
2. `muse-spark-1.3` on the Meta Model API — failover.
3. Verbatim heuristic — last resort, never an invented step.

Per-provider attempts are metered into the Admin LLMOps plane.

---

## Surfaces

| Surface | State | Notes |
| :--- | :--- | :--- |
| **Web sanctuary** (`web/`) | **Runs** | Next.js 14, the composer, the focus card, `/demo`, `/admin` |
| **WhatsApp** (`backend/app/main.py`) | **Runs** | Text, voice notes, photos, DONE/SKIP buttons |
| **Mobile** (`mobile/`) | **Runs** | Expo single-screen focus card + one multiline dump sheet |
| **watchOS** (`watch/watchos/`) | **Source only** | SwiftUI view + complication; no `.xcodeproj`, not built |
| **Lock-screen widget** (`watch/ios-widget/`) | **Source only** | WidgetKit source; not built |
| **Wear OS** (`watch/wearos/`) | **Not built** | Empty placeholder |

Media path: WhatsApp voice note or photo → Graph API download → Modal worker
(FFmpeg → 16 kHz WAV, Pillow → 1568 px JPEG) → Meta `/v1/responses` with
`muse-wonder-1.0` → transcript → the normal text pipeline.

> The OpenAI-compatible `/audio/transcriptions` and `/media/segmentation` routes
> return 404 on the Meta Model API. `/v1/responses` with an `input_audio` or
> `input_image` part is the route that answers; `muse-voice-transcribe-1.0` is
> listed by `GET /models` but is not routable there. This is verified against
> the live endpoint, not assumed.

---

## Architecture

```text
WhatsApp / web / mobile / watch
        │
        ▼
FastAPI executive core  ──  single-active invariant guard
        │
        ├── Baseten  meta-models/muse-spark-open-1026   (primary, open weights)
        ├── Meta     muse-spark-1.3                     (failover)
        ├── Meta     muse-wonder-1.0                    (voice + vision, /responses)
        └── Modal    FFmpeg / Pillow normalization
        │
        ▼
PostgreSQL (production) · SQLite (local)
```

---

## Quickstart

```bash
# backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env              # fill in the keys
cd backend && uvicorn app.main:app --reload     # :8000

# web
cd web && npm install && npm run dev            # :3000
```

`web/.env.local` needs `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_PHONE_NUMBER`, and a
server-side `ADMIN_API_KEY` (never `NEXT_PUBLIC_`).

### Tests

```bash
cd backend && python -m pytest -q      # 134 passed
cd web && npx tsc --noEmit             # clean
```

The suite never reaches a provider: every network seam is patched, so it runs
offline and in CI (`.github/workflows/ci.yml`).

---

## API

User endpoints take `X-Phone-Number` (MVP identity seam — see "Not built").
Operator endpoints take `X-Admin-Key`.

| Method & Path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /api/v1/focus` | phone | Active task + reserve **count** only |
| `POST /api/v1/tasks` | phone | `{ "dump": "…" }` (≤ 8000 chars) or `{ "title": "…" }` |
| `POST /api/v1/tasks/{id}/derive` | phone | Re-run triage for a task with no step |
| `POST /api/v1/tasks/{id}/complete` | phone | Idempotent completion, surfaces the next |
| `POST /api/v1/tasks/{id}/skip?mode=reserve\|archive` | phone | Park or retire |
| `POST /api/v1/demo/reset?mode=task\|dump` | none | Reset **only** `DEMO_PHONE` |
| `GET /api/v1/telemetry` | admin | Six-plane control room |
| `GET /api/v1/health` | none | Liveness |
| `GET/POST /webhook` | Meta | WhatsApp verify + inbound |

`POST /api/v1/tasks` returns `filed_count`, `stashed_count`, `activated`, and
`step_source`, so a surface can report a batch honestly instead of claiming one
task.

---

## Invariants

| # | Invariant | State |
| :--- | :--- | :--- |
| 1 | Single active task per user | **Enforced** — service guard + tests |
| 2 | Clients see a reserve count, never titles | **Enforced** |
| 3 | No overdue state; times are soft pills | **Partial** — no due dates modelled |
| 4 | Midnight sweep archives served work silently | **Runs** — `RUN_SCHEDULER=1` |
| 5 | One nudge after 180 stalled minutes, then silence | **Runs** — same scheduler |
| 6 | Exactly-once, idempotent completion | **Enforced** across web, mobile, WhatsApp |
| 7 | No passwords; phone OTP only | **Not built** — header identity is the MVP seam |

---

## Deploy

The public demo above runs on Modal. The production path is Render + Vercel.

**Modal (what the demo link uses)** — `infra/modal_api.py` serves the FastAPI
app as an ASGI endpoint with one container and a durable Modal Volume;
`infra/modal_web.py` serves the Next.js standalone build.

```bash
modal deploy infra/modal_api.py    # -> the API URL
modal deploy infra/modal_web.py    # -> the web URL
# then pin CORS to the web origin and redeploy the API:
#   $env:ONETHING_WEB_ORIGIN="https://<web>.modal.run"; modal deploy infra/modal_api.py
modal secret create onething-web-admin ADMIN_API_KEY=... SECRET_KEY=...
```

This host keeps SQLite on a **Modal Volume**, which is durable block storage
rather than the ephemeral disk that made SQLite a liability. It is still a
single-writer database pinned to `max_containers=1`, and it is the demo host,
not the production story.

**Render (production)** — `Dockerfile` + `render.yaml` (web service + managed
Postgres 16):

```bash
# Render -> New -> Blueprint -> point at this repo
# set MODEL_API_KEY, BASETEN_API_KEY, MODAL_WORKER_URL, ALLOWED_ORIGINS
```

**Vercel (production web)** — `web/vercel.json`; set `NEXT_PUBLIC_API_URL` to
the Render URL and `ADMIN_API_KEY` (server-side) to the backend's value.

**Media worker** — `modal deploy infra/modal_worker.py`, then set
`MODAL_WORKER_URL`.

Production uses PostgreSQL via `DATABASE_URL`; SQLite is local-dev and demo
only.

---

## What is not built

Stated plainly, because a judge should be able to trust the rest of this page:

- **Phone OTP / real auth.** `X-Phone-Number` is a spoofable header, documented
  as the MVP seam. Rate limiting is in-process (per worker), not distributed.
- **Wear OS.** Empty placeholder. watchOS and the lock-screen widget are source
  only — there is no `.xcodeproj` in the repo.
- **Billing.** No Stripe, no subscriptions. The Billing plane says
  `NOT CONNECTED`.
- **WebSockets / Redis.** Completion is idempotent over HTTP; there is no push
  fan-out and no Redis.
- **`/portal`.** Does not exist.
- **Media metering.** Voice/vision calls are not counted in the LLMOps plane
  (the row says `UNMETERED`).
- **WhatsApp credentials.** The webhook handshake is live (correct token
  echoes `hub.challenge`, wrong token 403) and inbound text runs the full
  pipeline. `WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID` are not
  configured in this environment, so an inbound voice note stops honestly at
  the Graph download and the user gets "I could not read that one." The media
  path itself (Graph bytes, Modal normalize, Meta `/v1/responses`) is
  exercised end-to-end with real audio and image bytes, not mocked.

---

## Design — Warm Industrial Minimalism

Erebus `#0C0D0E` · Carbon `#16181A` · Bone `#F9F8F6` · Focus Amber `#F59E0B` ·
Momentum Emerald `#10B981`. 1px hairlines, zero radius, JetBrains Mono for
labels and Geist/SF Pro for copy. Restrained motion; one living accent.

---

MIT licensed — see [`LICENSE`](./LICENSE). Original design document:
[`SPEC.md`](./SPEC.md) (kept for history; the README is the source of truth for
what exists).
