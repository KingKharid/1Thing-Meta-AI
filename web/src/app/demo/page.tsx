"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { DEMO_DUMP } from "../demo-dump";

type Mode = "task" | "dump";

/**
 * The judge's front door.
 *
 * Two honest entry points, because the product has two truths worth
 * showing. "One step" lands on a real active task. "A week becomes one"
 * clears the surface so the next dump is the thing that activates the
 * head — seeding a task there would make Invariant 1 hide the point.
 *
 * Nothing here fabricates a state: if the backend is down the page says
 * so and the buttons stay honest.
 */
export default function DemoPage() {
  const router = useRouter();
  const [busy, setBusy] = useState<Mode | null>(null);
  const [failed, setFailed] = useState(false);

  async function start(mode: Mode) {
    if (busy) return;
    setBusy(mode);
    setFailed(false);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "";
      const res = await fetch(`${base}/api/v1/demo/reset?mode=${mode}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      router.push(mode === "dump" ? "/?demo=dump" : "/");
      router.refresh();
    } catch {
      setFailed(true);
      setBusy(null);
    }
  }

  return (
    <div className="shell grid-overlay">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <a className="wordmark" href="/">
            1Thing
          </a>
          <span className="brand-rule" aria-hidden="true" />
          <span className="brand-sub mono">JUDGE&apos;S ENTRY</span>
        </div>
        <div className="topbar-status mono">
          <span className="status-chip">
            <i className="status-dot status-dot-steady" aria-hidden="true" />
            DEMO // RESETTABLE
          </span>
        </div>
      </header>

      <main className="focus-wrap">
        <div className="focus-column">
          <section className="focus-card" aria-label="Demo start">
            <div className="focus-head">
              <span className="focus-task mono">ONE PHYSICAL NEXT STEP</span>
            </div>

            <h1 className="focus-title">SEE IT WORK IN FIFTEEN SECONDS</h1>
            <p className="focus-sub">
              Every productivity app shows you the mountain. 1Thing refuses.
              Pick a door — both run against the live model, not a recording.
            </p>

            <div className="demo-steps" aria-label="How the demo works">
              <div className="demo-step">
                <span className="demo-step-index mono" aria-hidden="true">
                  01
                </span>
                <span className="demo-step-name mono">SEND THE WEEK</span>
                <span className="demo-step-sub mono">
                  ONE MESSY MESSAGE
                </span>
              </div>
              <span className="demo-step-arrow" aria-hidden="true">
                →
              </span>
              <div className="demo-step">
                <span className="demo-step-index mono" aria-hidden="true">
                  02
                </span>
                <span className="demo-step-name mono">NINE FILED</span>
                <span className="demo-step-sub mono">HIDDEN · NEVER LISTED</span>
              </div>
              <span className="demo-step-arrow" aria-hidden="true">
                →
              </span>
              <div className="demo-step">
                <span className="demo-step-index mono" aria-hidden="true">
                  03
                </span>
                <span className="demo-step-name mono">ONE STEP SHOWN</span>
                <span className="demo-step-sub mono">
                  DONE REVEALS THE NEXT
                </span>
              </div>
            </div>

            <div className="demo-doors">
              <div className="demo-door">
                <span className="demo-door-index mono" aria-hidden="true">
                  01
                </span>
                <button
                  type="button"
                  className="ingest-cta mono"
                  onClick={() => void start("task")}
                  disabled={busy !== null}
                >
                  {busy === "task" ? "RESETTING" : "SEE ONE STEP"}{" "}
                  <span aria-hidden="true">→</span>
                </button>
                <p className="demo-door-note">
                  Lands on one real task with its first physical move.
                  Press DONE — the next one is already waiting.
                </p>
              </div>

              <div className="demo-door">
                <span className="demo-door-index mono" aria-hidden="true">
                  02
                </span>
                <button
                  type="button"
                  className="ingest-cta mono"
                  onClick={() => void start("dump")}
                  disabled={busy !== null}
                >
                  {busy === "dump" ? "RESETTING" : "WATCH A WEEK BECOME ONE"}{" "}
                  <span aria-hidden="true">→</span>
                </button>
                <p className="demo-door-note">
                  Clears the surface and preloads a messy week. Press SEND and
                  the engine files nine things, shows one.
                </p>
              </div>
            </div>

            {failed && (
              <p className="composer-receipt is-error mono" role="alert">
                <i className="receipt-pip" aria-hidden="true" />
                THE ENGINE DID NOT ANSWER — TRY AGAIN
              </p>
            )}

            <div className="demo-dump-preview" aria-hidden="true">
              <span className="demo-dump-label mono">THE DUMP YOU CAN SEND</span>
              <pre className="demo-dump-text mono">{DEMO_DUMP}</pre>
            </div>

            <div className="card-foot mono">
              <span className="foot-item">NO SIGN-UP</span>
              <span className="foot-item">NO TASK LIST SHOWN</span>
            </div>
          </section>

          <p className="composer-note mono">
            RESET ONLY TOUCHES THE DEMO ACCOUNT. YOUR OWN CAPTURES ARE SAFE.
          </p>
        </div>
      </main>

      <footer className="footbar mono">
        <span className="footbar-item">
          <i className="foot-dot" aria-hidden="true" />
          NEVER SHOW THE MOUNTAIN
        </span>
        <a className="footbar-link mono" href="/">
          OPEN THE SANCTUARY <span aria-hidden="true">→</span>
        </a>
      </footer>
    </div>
  );
}
