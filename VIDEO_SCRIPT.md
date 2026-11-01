# 1Thing — 3-minute video, shot list

Total 180 seconds, 8 beats. Record one beat at a time, then assemble.
Screen recording + voiceover only (human mic or AI TTS). No slides,
no face cam, no fake latency — cut dead air, never speed-ramp.

Honesty rule for the whole video: narrate only what is on screen. The
model triages dumps; greetings are answered from stored state with no
model call; anything unbuilt is labeled, never hidden. If a beat shows
a greeting, say so (line provided below).

## Before you hit record

- [ ] Demo warm: open `/demo` once in the recording browser.
- [ ] Telemetry fresh: send one dump first so `BASETEN_CALLS_24H` is
  non-zero and `LAST_ENGINE_AGE` reads seconds, not hours.
- [ ] Reset `/demo` once so the state is clean.
- [ ] WhatsApp live (text + voice verified). If voice is down, use the
  fallback in the 1:45 beat — never simulate a voice reply.
- [ ] Browser 1440×900, 100% zoom, bookmarks bar hidden, notifications
  off, cursor visible, no personal data on screen.
- [ ] Recorder at 1080p/30. Voiceover: one clip per beat; respell model
  names phonetically until right; punctuate pauses with commas.
- [ ] One dry run end to end.

## The cut

### 0:00–0:15 — the problem

Capture: black screen, white mono text fading in. Nothing else.

Say: "Every task app eventually becomes another thing to manage.
Forty rows, red badges, a mountain you already knew about. I live in
that freeze — ADHD, founder burnout, a hundred open loops — so for
this hackathon I built for my own world. The problem was never the
list. It was choosing."

Serves: Impact (who it is for) + Stage 1 theme and new-work identity.

### 0:15–0:30 — the claim

Capture: cut to the sanctuary showing one card, one step. Hold still
for 5 seconds so the judge absorbs it.

Say: "This is 1Thing, built in ten days for the Meta hackathon under
Build for Your World. It shows exactly one physical next step.
Nothing else. Ever."

Serves: Stage 1 gate (theme, built-during-event stated on camera).

### 0:30–0:55 — the dump

Capture: click the composer, paste the ten-line week dump, let it sit
one beat. Keep the address bar visible for one second (proves live
product). Press SEND. Keep recording through the EXTRACTING counter.

Say: "So here is a real week. A dentist, a venue deposit, a birthday,
tax docs, a car, a promise I made, a flight, a dripping tap. One
message. The open-weights model reads all of it and decides what
comes first for me, right now."

Then cut the dead air (jump from ~12s of extracting to the result).

Serves: Demo (real latency, honestly cut) + Tooling (open-weights
named as the reasoning engine).

### 0:55–1:20 — the one thing

Capture: the result card — title, one step, minute pill. Slowly read
the step. Do not scroll; there is nothing below to show.

Say: "Nine things filed. One on screen. It did not just extract
tasks — it decided the order. It picked the dentist, the thing that
has been hurting for two weeks, and it did not give me a category.
It gave me a physical move. Open contacts, put the phone on speaker,
have the details ready to dial. That is not a task. That is the
first two minutes."

Serves: Impact (the product thesis) + Tooling (ordering is the
beyond-basic-integration argument).

### 1:20–1:45 — the next one

Capture: press DONE. Hold on the new card, then hover the reserve
count so judges see a number, never titles.

Say: "Done. And it already knew what was next. Eight more are filed.
I never see them. That is the whole product — the mountain is
captured, not displayed."

Serves: Tech Depth (Invariant 1 and 2, visible, not claimed).

### 1:45–2:15 — the same thing on WhatsApp

Capture: phone screen recording. Send the voice note, wait, show the
reply arriving with DONE and SKIP buttons. Show the transcript
becoming the step.

Say: "Same engine, no app to open. I speak. Meta's Muse Wonder
transcribes. The open-weights model triages. Voice note in, one
step out."

Serves: Demo (second surface, multimodal) + Tooling (Wonder named).

Fallback if voice is down: 1:45–2:00 press DONE a second time on web
(reserve 7 to 6); 2:00–2:15 show a task with NO STEP YET and the
DERIVE STEP button. Say: "And when the model cannot produce a step,
it says so instead of inventing one."

### 2:15–2:40 — the proof underneath

Capture: open `/admin`. Type the operator key on camera — do not cut
around it. Point the cursor at each named row as you say it.

Say: "Everything you just saw is metered. The primary engine is
Meta's Muse Spark Open, the ten-twenty-six release, served through
Baseten — also my entry for the open-weights bonus. Meta's Muse
Spark 1.3 is the failover. Nothing here was hand-ordered: the model
triages, DONE promotes the next task on its own, and the scheduler
runs the midnight sweep and the single stall nudge. Real, not
claimed. And where something is not built, it says so. That row is
honest."

Serves: Tech Depth (metering, scheduler, auth are real) + open-weights
verifiability + agentic autonomy, all on camera.

### 2:40–3:00 — close

Capture: back to the focus card. Hold 5 seconds. End card 3 seconds:
repo URL + demo URL as plain text.

Say: "1Thing is not a better to-do list. It is a refusal. One
physical next step, and never the mountain."

## Rules of the cut

- **No slides.** Screen + voice only.
- **No fake latency.** Cut, do not speed-ramp.
- **Greetings honesty.** If any beat shows a greeting like "hey", the
  reply comes from stored state with no model call. Say exactly that
  on camera: "That reply came from stored state — no model involved."
  Never imply the model answered it.
- **Say Meta's model names aloud** (Spark Open, Spark 1.3, Wonder).
  Judges scoring Tooling must not read them off a panel.
- **Failure state earns its place.** NO STEP YET is proof the product
  never invents a step — the cheapest craft signal in the video.
- **One take per beat**, then assemble.

## Upload

- YouTube unlisted or Vimeo, 1080p, captions on (fix the product name).
- Title: `1Thing — One Physical Next Step (Meta AI Hackathon)`
- Put the link in the submission form **and** the README.
