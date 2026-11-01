# The 3-minute video — shot list

25% of the score, and the only artifact most judges will consume. Record it
last, after the public URL works, so every frame is the real product.

## Before you hit record

- [ ] Public demo URL warm (open `/demo` once), telemetry live with fresh
  `LAST_ENGINE_AGE`. Send one dump first so `BASETEN_CALLS_24H` is non-zero.
- [ ] `https://<demo>/demo` reset once so the state is clean.
- [ ] WhatsApp segment: record it only if a real voice note is verified
  end-to-end; otherwise use the fallback in that section.
- [ ] Second monitor or phone in frame for the WhatsApp segment (if live).
- [ ] Browser at 1440×900, 100% zoom, no bookmarks bar, no other tabs.
- [ ] Notifications off. Cursor visible. No personal data on screen.
- [ ] Screen recorder at 1080p/30.
- [ ] Voiceover: human mic (quiet room, one test clip) or AI TTS (one clip
  per segment; respell model names phonetically until they sound right,
  and punctuate pauses with commas and periods).
- [ ] One dry run end to end. If extraction takes 15s, that is fine — cut it,
      do not fake it.

## The cut

### 0:00 – 0:15 — the problem

Black screen, white mono text, voiceover.

> "Every task app eventually becomes another thing to manage. Forty rows, red
> badges, a mountain you already knew about. I live in that freeze — ADHD,
> founder burnout, a hundred open loops — so for this hackathon I built for
> my own world. The problem was never the list. It was choosing."

### 0:15 – 0:30 — the claim

Cut to the sanctuary. One card, one step.

> "This is 1Thing, built in ten days for the Meta hackathon under Build for
> Your World. It shows exactly one physical next step. Nothing else. Ever."

### 0:30 – 0:55 — the dump

Click into the composer. Paste the ten-line week dump. Let it sit for a beat.

> "So here's a real week. A dentist, a venue deposit, a birthday, tax docs, a
> car, a promise I made, a flight, a dripping tap."

Press **SEND**. The hint reads `EXTRACTING` with a live second counter —
let it run on camera.

> "One message. The model is reading all of it and deciding what comes first
> for me, right now."

**Cut the dead air** at 12s — jump to the result. Never fake the speed; just
cut.

### 0:55 – 1:20 — the one thing

The card: `Call dentist about painful crown`, one step, `10 MIN`.

> "Nine things filed. One on screen. It didn't just extract tasks — it
> decided the order. It picked the dentist, the thing that has been hurting
> for two weeks, and it didn't give me a category. It gave me a physical
> move."

Read the step aloud, slowly.

> "Open contacts, put the phone on speaker, have the details ready to dial.
> That's not a task. That's the first two minutes."

### 1:20 – 1:45 — the next one

Press **DONE**. The card swaps to the venue deposit. Reserve drops 8 → 7 —
hover the count so judges see a number, never titles.

> "Done. And it already knew what was next. Eight more are filed. I never see
> them. That's the whole product — the mountain is captured, not displayed."

### 1:45 – 2:15 — the same thing on WhatsApp (only if live)

Record this segment only after a real voice note is verified end-to-end
(`WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_PHONE_NUMBER_ID` set, transcript →
tasks confirmed). Cut to the phone. Send a voice note:

> "Remind me to book the flight for the offsite, and pick up the dry cleaning
> before Thursday."

Show the reply: one step, with DONE / SKIP buttons.

> "Same engine, no app to open. Meta's Muse Wonder transcribed the voice,
> the open-weights model triaged it. Voice note in, one step out."

Fallback if WhatsApp is not live: 1:45–2:00, press DONE a second time on
web (reserve 7 → 6); 2:00–2:15, show the honest failure state — a task with
`NO STEP YET` and the `DERIVE STEP` button. Do not simulate a voice reply —
an unverified hero moment costs more than it gains.

### 2:15 – 2:40 — the proof underneath

Cut to `/admin`. It asks for the operator key — type it, do not cut around it.

> "Everything you just saw is metered. The primary engine is Meta's Muse
> Spark Open — `muse-spark-open-1026`, open weights, served through Baseten,
> which is also my entry for the open-weights bonus. Meta's Muse Spark 1.3
> is the failover. Nothing here was hand-ordered: the model triages, DONE
> promotes the next task on its own, and the scheduler runs the midnight
> sweep and the single stall nudge. Real, not claimed."

Point at `PRIMARY_ENGINE // BASETEN // OPEN WEIGHTS`, `LAST_ENGINE` with a
fresh `LAST_ENGINE_AGE`, `SCHEDULER // RUNNING`, and `PHONE_OTP // NOT BUILT`.

> "And where something isn't built, it says so. That row is honest."

### 2:40 – 3:00 — close

Back to the focus card.

> "1Thing isn't a better to-do list. It's a refusal. One physical next step,
> and never the mountain."

End card: repo URL + demo URL, 3 seconds.

## Rules of the cut

- **No slides.** Screen + voice only.
- **No fake latency.** Cut, don't speed-ramp.
- **Show the failure state once** — `NO STEP YET` on a task with no step
  (or as the WhatsApp-fallback filler). It is the most credible five
  seconds in the video: proof the product never invents a step.
- **Say the model names out loud.** Judges scoring "use of Meta AI tooling"
  should not have to read them off a panel.
- **One take per segment**, then assemble. Re-recording the whole thing invites
  mistakes.

## Upload

- YouTube unlisted or Vimeo, 1080p, captions on (auto is fine, fix the product
  name).
- Title: `1Thing — One Physical Next Step (Meta AI Hackathon)`
- Put the link in the submission form **and** the README.
