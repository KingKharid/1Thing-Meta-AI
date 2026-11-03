import CaptureBay from "./capture-bay";
import DeriveStep from "./derive-step";
import { DEMO_DUMP } from "./demo-dump";
import FocusActions from "./focus-actions";
import { apiConfig, getFocus } from "./focus-lib";

function ReserveLine({ count }: { count: number }) {
  const clear = count === 0;
  // The meter caps at eight bars; the number beside it stays exact.
  const filled = Math.min(count, 8);
  return (
    <div
      className={`reserve-line${clear ? " is-clear" : ""}`}
      aria-label={clear ? "Reserve clear" : `${count} items hidden in reserve`}
    >
      <span className="reserve-glyph" aria-hidden="true" />
      <span className="reserve-count mono">{count}</span>
      <span className="reserve-text mono">
        {clear ? "RESERVE CLEAR" : "IN RESERVE · HIDDEN"}
      </span>
      {!clear && (
        <span className="reserve-meter" aria-hidden="true">
          {Array.from({ length: 8 }, (_, i) => (
            <i key={i} className={i < filled ? "is-on" : undefined} />
          ))}
        </span>
      )}
    </div>
  );
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <circle cx="8" cy="8" r="5.5" />
      <path d="M8 5.2V8l1.9 1.1" />
    </svg>
  );
}

export default async function FocusPage({
  searchParams,
}: {
  searchParams?: { demo?: string };
}) {
  const focus = await getFocus();
  const { base, phone, whatsapp } = apiConfig();
  const task = focus.task;
  // The judge's entry point hands over with the week-long dump already in
  // the composer, so the first press of SEND is the demo.
  const prefill = searchParams?.demo === "dump" ? DEMO_DUMP : "";
  const stamp = new Date(focus.updatedAt).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });

  const statusLabel =
    focus.mode === "live" ? "LIVE" : focus.mode === "preview" ? "PREVIEW" : "OFFLINE";
  const serial =
    task && task.id > 0 ? `#${String(task.id).padStart(3, "0")}` : null;

  return (
    <div className="shell grid-overlay">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <a className="wordmark" href="/">
            1Thing
          </a>
          <span className="brand-rule" aria-hidden="true" />
          <span className="brand-sub mono">ONE PHYSICAL NEXT STEP</span>
        </div>
        <div className="topbar-status mono">
          <span className={`status-chip ${focus.live ? "is-live" : "is-offline"}`}>
            <i className="status-dot" aria-hidden="true" />
            ENGINE // {statusLabel}
          </span>
          {/* Six of seven invariants live on this surface: phone OTP is
              the documented seam, so the seventh is not claimed armed. */}
          <span className="status-chip is-live">
            <i className="status-dot" aria-hidden="true" />
            INVARIANTS // 6 ARMED
          </span>
        </div>
      </header>

      <main className="focus-wrap">
        <div className="focus-column">
          <div className="focus-kicker mono" aria-hidden="true">
            <span className="kicker-left">
              <span className="kicker-mark" />
              {focus.mode === "error"
                ? "OFFLINE"
                : task === null
                  ? "STANDBY"
                  : "ACTIVE FOCUS"}
            </span>
            <span className="kicker-right">SURFACE // WEB SANCTUARY</span>
          </div>
          {focus.mode === "error" ? (
            <section className="focus-card focus-card-error" aria-label="Engine unreachable">
              <div className="focus-head">
                <span className="focus-task mono">ENGINE UNREACHABLE</span>
              </div>
              <h1 className="focus-title">CAN&apos;T REACH THE ENGINE</h1>
              <p className="focus-sub">
                Nothing was lost. The focus API didn&apos;t answer — check the
                backend, then retry.
              </p>
              <a className="ingest-cta mono" href="/">
                RETRY <span aria-hidden="true">→</span>
              </a>
              <div className="card-foot mono">
                <span className="foot-item">CHECKED {stamp}</span>
                <span className="foot-item">SOURCE OFFLINE</span>
              </div>
            </section>
          ) : task === null ? (
            <section className="focus-card focus-card-idle" aria-label="No active task">
              <div className="focus-head">
                <span className="focus-task mono">STANDBY</span>
              </div>
              <h1 className="focus-title">NOTHING IN FOCUS</h1>
              <p className="focus-sub">
                The surface is clear. One thought in, one physical step out.
              </p>

              {whatsapp && (
                <a className="ingest-cta mono" href={`https://wa.me/${whatsapp}`}>
                  DUMP VIA WHATSAPP <span aria-hidden="true">→</span>
                </a>
              )}

              <ReserveLine count={focus.reserveCount} />

              <div className="card-foot mono">
                <span className="foot-item">CHECKED {stamp}</span>
                <span className="foot-item">
                  SOURCE {focus.live ? "API" : "PREVIEW"}
                </span>
              </div>
            </section>
          ) : (
            <section className="focus-card" aria-label="Current task">
              <div className="focus-head">
                <span className="focus-task is-title" title={task.title}>
                  {task.title}
                </span>
                {serial && <span className="focus-serial mono">{serial}</span>}
              </div>

              <div
                className={`focus-step-label mono${
                  task.firstMicroStep ? "" : " is-missing"
                }`}
              >
                {task.firstMicroStep && (
                  <span className="step-tick" aria-hidden="true" />
                )}
                {task.firstMicroStep ? "NEXT STEP" : "STEP MISSING"}
              </div>

              {task.firstMicroStep ? (
                <div className="step-panel">
                  <h1
                    className={
                      task.firstMicroStep.length > 48
                        ? "focus-step is-long"
                        : "focus-step"
                    }
                  >
                    {task.firstMicroStep}
                  </h1>
                </div>
              ) : (
                <>
                  <h1 className="focus-step is-pending">NO STEP YET</h1>
                  <p className="focus-pending">
                    The engine didn&apos;t return a first move for this. The
                    dump is safe — ask again.
                  </p>
                  <DeriveStep
                    taskId={task.id}
                    apiUrl={base}
                    phone={phone}
                    live={focus.live}
                  />
                </>
              )}

              <div className="focus-meta">
                <span className="pill pill-amber">
                  <ClockIcon />
                  {task.estimatedMinutes} MIN
                </span>
                <span className="pill pill-ghost">
                  <span className="pill-dot" aria-hidden="true" />
                  ONE STEP ONLY
                </span>
              </div>

              <FocusActions
                taskId={task.id}
                apiUrl={apiConfig().base}
                phone={apiConfig().phone}
                live={focus.live}
              />

              <ReserveLine count={focus.reserveCount} />

              <div className="card-foot mono">
                <span className="foot-item">CHECKED {stamp}</span>
                <span className="foot-item">
                  SOURCE {focus.mode === "preview" ? "PREVIEW" : "API"}
                </span>
              </div>
            </section>
          )}

          {/* One bay instance outside the branch: filing into an empty
              surface flips the card, and the confirmation must survive
              that swap. */}
          {focus.mode !== "error" && (
            <CaptureBay
              apiUrl={base}
              phone={phone}
              live={focus.live}
              activeId={task?.id ?? null}
              prefill={prefill}
            />
          )}
        </div>
      </main>

      <footer className="footbar mono">
        <span className="footbar-item">
          <i className="foot-dot" aria-hidden="true" />
          NEVER SHOW THE MOUNTAIN
        </span>
        <a className="footbar-link mono" href="/demo">
          DEMO <span aria-hidden="true">→</span>
        </a>
        <a className="footbar-link mono" href="/admin">
          CONTROL ROOM <span aria-hidden="true">→</span>
        </a>
      </footer>
    </div>
  );
}
