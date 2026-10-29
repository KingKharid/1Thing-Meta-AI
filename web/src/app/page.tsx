import CaptureBay from "./capture-bay";
import DeriveStep from "./derive-step";
import FocusActions from "./focus-actions";
import { apiConfig, getFocus } from "./focus-lib";

function ReserveLine({ count }: { count: number }) {
  const clear = count === 0;
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

export default async function FocusPage() {
  const focus = await getFocus();
  const { base, phone, whatsapp } = apiConfig();
  const task = focus.task;
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
        </div>
      </header>

      <main className="focus-wrap">
        <div className="focus-column">
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
                <span className="focus-task mono" title={task.title}>
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
                <h1
                  className={
                    task.firstMicroStep.length > 48
                      ? "focus-step is-long"
                      : "focus-step"
                  }
                >
                  {task.firstMicroStep}
                </h1>
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
                <span className="pill">
                  <ClockIcon />
                  {task.estimatedMinutes} MIN
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
            <CaptureBay apiUrl={base} phone={phone} live={focus.live} />
          )}
        </div>
      </main>

      <footer className="footbar mono">
        <span className="footbar-item">
          <i className="foot-dot" aria-hidden="true" />
          NEVER SHOW THE MOUNTAIN
        </span>
        <a className="footbar-link mono" href="/admin">
          CONTROL ROOM <span aria-hidden="true">→</span>
        </a>
      </footer>
    </div>
  );
}
