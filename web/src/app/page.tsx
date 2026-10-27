import FocusActions from "./focus-actions";
import { apiConfig, getFocus } from "./focus-lib";

export default async function FocusPage() {
  const focus = await getFocus();
  const { base, phone } = apiConfig();
  const task = focus.task;

  return (
    <div className="shell grid-overlay">
      <header className="topbar">
        <div className="wordmark">1Thing</div>
        <div className="topbar-status mono">
          <span>ENGINE // {focus.live ? "LIVE" : "OFFLINE PREVIEW"}</span>
          <span>INVARIANTS // 7 ARMED</span>
        </div>
      </header>

      <main className="focus-wrap">
        <div className="focus-column">
          <div className="focus-kicker mono">
            <span>ACTIVE FOCUS</span>
            <span>SURFACE // WEB SANCTUARY</span>
          </div>

          {task === null ? (
            <section className="focus-card" aria-label="No active task">
              <h1 className="focus-title">NOTHING IN FOCUS</h1>
              <div className="focus-step mono">▸ SEND A VOICE NOTE OR BRAIN DUMP TO BEGIN</div>
              <div className="reserve-line mono">
                RESERVE: {focus.reserveCount} ITEMS IN STASIS (HIDDEN)
              </div>
            </section>
          ) : (
            <section className="focus-card" aria-label="Current task">
              <h1 className="focus-title">{task.title}</h1>
              <div className="focus-step mono">▸ {task.firstMicroStep}</div>
              <div className="focus-meta">
                <span className="pill pill-amber">[{task.estimatedMinutes}M]</span>
                <span className="pill">ONE STEP</span>
              </div>
              <div className="reserve-line mono">
                RESERVE: {focus.reserveCount} ITEMS IN STASIS (HIDDEN)
              </div>
              <FocusActions taskId={task.id} apiUrl={base} phone={phone} live={focus.live} />
            </section>
          )}
        </div>
      </main>

      <footer className="footbar mono">
        <span>SINGLE-ACTIVE INVARIANT ARMED</span>
        <span>NEVER SHOW THE MOUNTAIN</span>
      </footer>
    </div>
  );
}
