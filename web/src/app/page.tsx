import FocusActions from "./focus-actions";
import { apiConfig, getFocus } from "./focus-lib";

const METER_MAX = 8;

function ReserveRow({ count }: { count: number }) {
  return (
    <div className="reserve-row">
      <div className="reserve-info">
        <span className="reserve-label mono">RESERVE</span>
        <span className="reserve-value mono">
          {count} {count === 1 ? "ITEM" : "ITEMS"} IN STASIS
          <span className="reserve-hint"> · HIDDEN</span>
        </span>
      </div>
      <span className="meter" aria-hidden="true">
        {count === 0 ? (
          <span className="mono meter-clear">
            <i />
            CLEAR
          </span>
        ) : (
          <>
            {Array.from({ length: Math.min(count, METER_MAX) }).map((_, i) => (
              <i key={i} style={{ animationDelay: `${i * 45}ms` }} />
            ))}
            {count > METER_MAX && (
              <span className="mono meter-more">+{count - METER_MAX}</span>
            )}
          </>
        )}
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
  const { base, phone } = apiConfig();
  const task = focus.task;
  const syncedAt = new Date().toISOString().slice(11, 19);
  const focusLabel =
    task === null
      ? "STANDBY — NO ACTIVE FOCUS"
      : task.id < 0
        ? "ACTIVE FOCUS"
        : `ACTIVE FOCUS — #${String(task.id).padStart(3, "0")}`;

  return (
    <div className="shell grid-overlay">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="wordmark">1Thing</span>
          <span className="brand-rule" aria-hidden="true" />
          <span className="brand-sub mono">ONE PHYSICAL NEXT STEP</span>
        </div>
        <div className="topbar-status mono">
          <span className={`status-chip ${focus.live ? "is-live" : "is-offline"}`}>
            <i className="status-dot" aria-hidden="true" />
            ENGINE // {focus.live ? "LIVE" : "OFFLINE PREVIEW"}
          </span>
          <span className="status-chip">
            <i className="status-dot status-dot-steady" aria-hidden="true" />
            INVARIANTS // 7 ARMED
          </span>
        </div>
      </header>

      <main className="focus-wrap">
        <div className="focus-column">
          <div className="focus-kicker mono">
            <span className="kicker-left">
              <span className="kicker-mark" aria-hidden="true" />
              {focusLabel}
            </span>
            <span className="kicker-right">SURFACE // WEB SANCTUARY</span>
          </div>

          {task === null ? (
            <section className="focus-card focus-card-idle" aria-label="No active task">
              <h1 className="focus-title">NOTHING IN FOCUS</h1>
              <p className="focus-sub">
                The surface is clear. Dump anything — voice, snap, or text — and
                the system returns one physical next step.
              </p>

              <div className="ingest-bay" aria-label="Awaiting input">
                <span className="ingest-target" aria-hidden="true">
                  <span className="ingest-target-ring" />
                  <span className="ingest-target-pip" />
                </span>
                <div className="ingest-copy">
                  <span className="ingest-title mono">AWAITING INPUT</span>
                  <span className="ingest-line">ANY FORMAT IN · ONE PHYSICAL STEP OUT</span>
                </div>
                <div className="ingest-channels">
                  <span className="channel-chip mono">WHATSAPP</span>
                  <span className="channel-chip mono">WEB</span>
                  <span className="channel-chip mono">WATCH</span>
                </div>
              </div>

              <ReserveRow count={focus.reserveCount} />

              <div className="hint-block">
                <div className="kv">
                  <span className="kv-key">
                    <i className="kv-dot" aria-hidden="true" />
                    INGEST
                  </span>
                  <span className="kv-val">VOICE / SNAP / TEXT READY</span>
                </div>
                <div className="kv">
                  <span className="kv-key">
                    <i className="kv-dot" aria-hidden="true" />
                    CHANNELS
                  </span>
                  <span className="kv-val">WHATSAPP / WEB / WATCH</span>
                </div>
                <div className="kv">
                  <span className="kv-key">
                    <i className="kv-dot" aria-hidden="true" />
                    INVARIANT
                  </span>
                  <span className="kv-val">SINGLE-ACTIVE ARMED</span>
                </div>
              </div>

              <div className="card-foot mono">
                <span className="foot-item">
                  <i className="foot-dot" aria-hidden="true" />
                  SYNC // {syncedAt} UTC
                </span>
                <span className="foot-item">SOURCE // {focus.live ? "API" : "OFFLINE"}</span>
              </div>
            </section>
          ) : (
            <section className="focus-card" aria-label="Current task">
              <h1 className="focus-title">{task.title}</h1>
              <div className="step-strip">
                <span className="step-label mono">NEXT PHYSICAL STEP</span>
                <div className="step-body">
                  <span className="livepip" aria-hidden="true" />
                  <span className="step-text mono">{task.firstMicroStep}</span>
                </div>
              </div>
              <div className="focus-meta">
                <span className="pill pill-amber">
                  <ClockIcon />
                  {task.estimatedMinutes} MIN
                </span>
                <span className="pill">
                  <span className="pill-dot" aria-hidden="true" />
                  ONE STEP ONLY
                </span>
              </div>
              <ReserveRow count={focus.reserveCount} />
              <FocusActions taskId={task.id} apiUrl={base} phone={phone} live={focus.live} />
              <div className="card-foot mono">
                <span className="foot-item">
                  <i className="foot-dot" aria-hidden="true" />
                  SYNC // {syncedAt} UTC
                </span>
                <span className="foot-item">SOURCE // {focus.live ? "API" : "OFFLINE"}</span>
              </div>
            </section>
          )}
        </div>
      </main>

      <footer className="footbar mono">
        <span className="footbar-item">
          <i className="foot-dot" aria-hidden="true" />
          SINGLE-ACTIVE INVARIANT ARMED
        </span>
        <span className="footbar-item">NEVER SHOW THE MOUNTAIN</span>
      </footer>
    </div>
  );
}
