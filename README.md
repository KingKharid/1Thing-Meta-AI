# 1Thing — One Physical Next Step, Everywhere

> **Meta Global AI Developer Hackathon submission — Indie Developer track.**
> Public repository: [KingKharid/1Thing-Meta-AI](https://github.com/KingKharid/1Thing-Meta-AI)

1Thing is an omnipresent, voice-first multimodal executive gatekeeper for ADHD adults,
overwhelmed founders, and chronic procrastinators. Raw multimodal chaos — WhatsApp voice
notes, whiteboard snapshots, camera uploads, share sheets, brain dumps — enters the
ingestion layer, and the multi-cloud AI core returns **strictly ONE physical micro-action
item** across every surface (watch, lock screen, phone, WhatsApp, web sanctuary), while
the reserve backlog stays completely invisible.

**Core invariant:** *"Never show the mountain. One physical next step, everywhere."*

Full engineering specification: [`SPEC.md`](./SPEC.md).

## Monorepo Layout

```text
1Thing-Meta-AI/
├── backend/app/        # FastAPI executive core (main.py, meta_client.py)
├── web/src/app/        # Next.js sanctuary, demo, portal, admin
├── mobile/             # Expo single-screen focus interface
├── watch/              # watchOS (SwiftUI) + Wear OS (Compose) apps
└── infra/              # Modal serverless media worker
```

## Multi-Cloud Architecture

Workloads are distributed across specialized inference partners so high-value tokens are
preserved exclusively for core reasoning and live demos, while heavy media handling is
offloaded to Modal serverless workers.

```text
INGESTION (WhatsApp audio/text, camera snapshots)
        │
        ▼
MODAL SERVERLESS WORKER — audio normalization (FFmpeg), image resize/compress
        │
        ├──────────────────────┴──────────────────────┐
        ▼                                             ▼
META MODEL API ($150)                    BASETEN PARTNER ($100 + 2M TPM)
- Muse Voice Transcribe                   - meta-models/muse-spark-open-1026
- SAM 3.1 & Muse Image                      (open-weights reasoning engine)
- Muse Spark 1.3 / Wonder
        │                                             │
        └──────────────────────┬──────────────────────┘
                               ▼
        SINGLE-ACTIVE INVARIANT ENGINE (FastAPI)
        Strictly 1 active task per user
```

| Provider | Credit Pool | Role | Models & Endpoints |
| :--- | :--- | :--- | :--- |
| **Meta Model API** | $150 | Core hosted intelligence & transcription | `muse-voice-transcribe-1.0`, `sam-3.1`, `muse-spark-1.3`, `muse-wonder-1.0` |
| **Baseten** | $100 + 2M TPM | Open-weights reasoning engine & bonus eligibility | `meta-models/muse-spark-open-1026` via `https://inference.baseten.co/v1` |
| **Modal** | $30/mo free tier | Async media pre-processing | `infra/modal_worker.py` (FFmpeg audio, image compression) |

## Design System — Warm Industrial Minimalism

No cookie-cutter SaaS aesthetics: no purple gradients, no generic AI cards. Every
surface (web sanctuary, admin control room, mobile, watch, lock screen, widgets)
follows these tokens:

| Token | Value |
| :--- | :--- |
| Background (Erebus) | `#0C0D0E` |
| Surface / Containers (Carbon) | `#16181A` |
| Typography / Primary Text (Bone) | `#F9F8F6` |
| Accent / Active Focus (Focus Amber) | `#F59E0B` |
| Completion / Success (Momentum Emerald) | `#10B981` |
| Structural Borders | `1px solid rgba(249, 248, 246, 0.08)` |

- **Typography:** `JetBrains Mono` for micro-labels, data readouts, status codes, and
  timestamps; `Geist` / `SF Pro` for body, headers, and UI copy.
- **Geometry:** flat surfaces, structural paper grid, stark 1px borders, zero
  border-radius pills or soft shadows; generous 24–32px negative space.
- **Feedback:** instantaneous 50ms tactile response on every state transition
  (Done, Skip, Chunk).

## Quickstart (Backend)

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows; use source .venv/bin/activate on macOS/Linux
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload  # serves on http://localhost:8000
```

Required environment variables: `MODEL_API_KEY`, `BASETEN_API_KEY`,
`WHATSAPP_VERIFY_TOKEN`. See `backend/app/meta_client.py` for the full client.
Optional: `DATABASE_URL` (defaults to local SQLite; use
`postgresql+psycopg://...` in production).

```bash
cd backend
../.venv/Scripts/python -m pytest tests -v  # invariant suite
```

## Quickstart (Web Sanctuary)

```bash
cd web
npm install
npm run dev  # serves on http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` (e.g. `http://localhost:8000`) to light the views
with live backend data; without it the sanctuary renders offline fallback
content. `/admin` hosts the six-plane control room.

## API Surface

Identity header for user endpoints: `X-Phone-Number` (MVP seam for phone-OTP
sessions). Reserve payloads expose the active task plus a count only.

| Method & Path | Purpose |
| :--- | :--- |
| `GET /api/v1/focus` | Active task + hidden reserve count |
| `POST /api/v1/tasks/{id}/complete` | Idempotent completion, surfaces next queued task |
| `POST /api/v1/tasks/{id}/skip?mode=reserve\|archive` | Skip back to reserve (default) or archive |
| `GET /api/v1/telemetry` | Six-plane control-room stats (no auth) |
| `GET /api/v1/health` | Engine status |

## Companion Scaffolds

- `mobile/` — Expo focus interface (`App.js` + `FocusCard` + ingestion dock).
  Runs against the same API via `EXPO_PUBLIC_API_URL`.
- `watch/watchos/` — SwiftUI focus view + 16-char WidgetKit complication
  skeleton; companion sync phase wires `URLSession` to `/api/v1/focus`.

## Product Invariants

1. Single active task per user, enforced at database and service layer.
2. Clients see the active task plus a reserve *count* — never reserve titles.
3. No overdue state; scheduled times are soft pills.
4. Midnight sweep archives served/skipped work silently.
5. One nudge after 180 stalled minutes, then silence.
6. Exactly-once, idempotent completion fanning out over WebSockets.
7. No passwords — phone OTP only; zero-login Stripe billing.
