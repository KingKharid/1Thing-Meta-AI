# The 3-minute video — shot list

25% of the score, and the only artifact most judges will consume. Record it
last, after the public URL works, so every frame is the real product.

## Before you hit record

- [ ] Public demo URL live, backend on PostgreSQL, `RUN_SCHEDULER=1`.
- [ ] `https://<demo>/demo` reset once so the state is clean.
- [ ] WhatsApp number live and able to receive a voice note.
- [ ] Second monitor or phone in frame for the WhatsApp segment.
- [ ] Browser at 1440×900, 100% zoom, no bookmarks bar, no other tabs.
- [ ] Notifications off. Cursor visible. No personal data on screen.
- [ ] Screen recorder at 1080p/30. Mic tested. Room quiet.
- [ ] One dry run end to end. If extraction takes 15s, that is fine — cut it,
      do not fake it.

## The cut

### 0:00 – 0:15 — the problem

Black screen, white mono text, your voice.

> "Every task app eventually becomes another thing to manage. Forty rows, red
> badges, a mountain you already knew about. The problem was never the list.
> It was choosing."

### 0:15 – 0:30 — the claim

Cut to the sanctuary. One card, one step.

> "This is 1Thing. It shows exactly one physical next step. Nothing else.
> Ever."

### 0:30 – 0:55 — the dump

Click into the composer. Paste the ten-line week dump. Let it sit for a beat.

> "So here's a real week. A dentist, a venue deposit, a birthday, tax docs, a
> car, a promise I made, a flight, a dripping tap."

Press **SEND**. The hint reads `EXTRACTING · 7S`. Let the counter run.

> "One message. The model is reading all of it and deciding what comes first
> for me, right now."

**Cut the dead air** at 12s — jump to the result. Never fake the speed; just
cut.

### 0:55 – 1:20 — the one thing

The card: `Call dentist about painful crown`, one step, `10 MIN`.

> "Nine things filed. One on screen. It picked the dentist — the thing that has
> been hurting for two weeks — and it didn't give me a category. It gave me a
> physical move."

Read the step aloud, slowly.

> "Open contacts, put the phone on speaker, have the details ready to dial.
> That's not a task. That's the first two minutes."

### 1:20 – 1:45 — the next one

Press **DONE**. The card swaps to the venue deposit. Reserve drops 8 → 7.

> "Done. And it already knew what was next. Eight more are filed. I never see
> them. That's the whole product — the mountain is captured, not displayed."

### 1:45 – 2:15 — the same thing on WhatsApp

Cut to the phone. Send a voice note:

> "Remind me to book the flight for the offsite, and pick up the dry cleaning
> before Thursday."

Show the reply: one step, with DONE / SKIP buttons.

> "Same engine, no app to open. Voice note in, one step out."

### 2:15 – 2:40 — the proof underneath

Cut to `/admin`. It asks for the operator key — type it, do not cut around it.

> "Everything you just saw is metered. Baseten open weights is the primary
> engine — that's `muse-spark-open-1026`, open weights, which is the other
> track I'm entering. Meta's hosted model is the failover. The scheduler is
> running, so the midnight sweep and the single stall nudge are real, not
> claimed."

Point at `PRIMARY_ENGINE // BASETEN // OPEN WEIGHTS`, `SCHEDULER // RUNNING`,
and `PHONE_OTP // NOT BUILT`.

> "And where something isn't built, it says so. That row is honest."

### 2:40 – 3:00 — close

Back to the focus card.

> "1Thing isn't a better to-do list. It's a refusal. One physical next step,
> and never the mountain."

End card: repo URL + demo URL, 3 seconds.

## Rules of the cut

- **No slides.** Screen + voice only.
- **No fake latency.** Cut, don't speed-ramp.
- **Show the failure state once** if you can — `NO STEP YET` on a task with no
  step. It is the most credible five seconds in the video.
- **Say the model names out loud.** Judges scoring "use of Meta AI tooling"
  should not have to read them off a panel.
- **One take per segment**, then assemble. Re-recording the whole thing invites
  mistakes.

## Upload

- YouTube unlisted or Vimeo, 1080p, captions on (auto is fine, fix the product
  name).
- Title: `1Thing — One Physical Next Step (Meta AI Hackathon)`
- Put the link in the submission form **and** the README.
