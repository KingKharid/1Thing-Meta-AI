# 1Thing — submission copy

Paste-ready text for the hackathon form. Replace the two placeholders before
submitting.

---

## Title

**1Thing — the app that refuses to show you the mountain**

## One-liner (≤ 200 chars)

Dump a whole week of chaos in one message. The model files all of it, hides it,
and puts exactly one physical next step on screen. Press DONE — the next one
appears.

## Track

Indie Developer

## Theme

Build for Your World

## Short description (≈ 100 words)

Every task app eventually becomes another thing to manage: forty rows, red
badges, a mountain you already knew about. 1Thing takes the opposite bet. You
empty a week of loose ends into one message — typed, spoken as a WhatsApp voice
note, or photographed — and the model extracts every distinct task, orders them
by what you can actually start now, and shows exactly one physical micro-step.
Everything else is filed into a hidden reserve and never displayed. Press DONE
and the next one surfaces, in the model's order. The product is a constraint,
not a feature: never show the mountain.

## Long description

**The problem.** Executive dysfunction is not a planning problem. People with
ADHD, burnout, or a hundred open loops already know what is on the list. What
they cannot do is choose. Every tool answers "what is on my plate?" — which is
the exact question that causes the freeze.

**What 1Thing does.** It answers "what is the one physical thing I do next?"
and refuses to answer anything else. The reserve backlog is stored but never
rendered; the API returns a count, not titles, so no client can leak it.

**How the model is used.** A dump is not a task, so the extraction contract
returns an ordered array, not one object. `triage.extract()` asks the model to
find every distinct commitment, write the exact two-minute physical action for
each, estimate time and energy, and order the array by what this person should
do first given the hour and their recent rhythm. The head is activated; the
rest are filed in the model's order. The order is the product — there is no
separate ranking heuristic to drift from it.

**Open weights first.** Every extraction tries `meta-models/muse-spark-open-1026`
on Baseten first, falls back to `muse-spark-1.3` on the Meta Model API, and
falls back again to a verbatim heuristic that files the person's own words
rather than inventing a step. Per-provider attempts are metered into a live
LLMOps plane, so the routing claim is visible rather than asserted.

**Multimodal, verified.** WhatsApp voice notes and photos go Graph API → Modal
(FFmpeg to 16 kHz WAV, Pillow to 1568 px JPEG) → Meta `/v1/responses` with
`muse-wonder-1.0`. Note that the OpenAI-compatible `/audio/transcriptions` and
`/media/segmentation` routes 404 on this API; `/v1/responses` with an
`input_audio`/`input_image` part is the route that actually answers.

**Honesty as an engineering constraint.** If the model cannot produce a step,
the card says `NO STEP YET` and offers `DERIVE STEP` — it never shows a
placeholder. If both providers fail, the receipt says the dump is still there
and the send button retries it. The admin plane marks billing `NOT CONNECTED`
and phone OTP `NOT BUILT` instead of showing a plausible zero.

**What is real today.** A FastAPI core with a single-active-task guard,
idempotent completion, a midnight sweep and one-shot stall nudge on a real
scheduler, PostgreSQL in production, 134 passing tests, a Next.js sanctuary
with a `/demo` judge entry, an Expo client, and a six-plane control room with
admin auth and rate limiting. Wear OS, `/portal`, WebSockets, Redis, Stripe and
phone OTP are explicitly not built and listed as such.

## Built with

Python · FastAPI · SQLAlchemy · PostgreSQL · Next.js 14 · TypeScript · Expo /
React Native · Meta Model API (Muse Spark 1.3, Muse Wonder) · Baseten open
weights (`muse-spark-open-1026`) · Modal · WhatsApp Cloud API · Docker ·
Render · Vercel · GitHub Actions

## Links

- Repo: https://github.com/KingKharid/1Thing-Meta-AI
- Demo: `<!-- TODO -->`
- Video: `<!-- TODO -->`

## What I would build next

1. Real phone OTP so `X-Phone-Number` stops being a spoofable seam.
2. Queue-and-poll extraction, so a 15-second model call never holds an HTTP
   request open.
3. Metering for voice/vision calls (the LLMOps plane currently says
   `UNMETERED` for them).
4. A watchOS target with an actual Xcode project — the SwiftUI source exists,
   the project does not.
