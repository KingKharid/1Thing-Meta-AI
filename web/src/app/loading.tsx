export default function Loading() {
  return (
    <div className="shell grid-overlay" aria-busy="true" aria-label="Loading focus">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="wordmark">1Thing</span>
          <span className="brand-rule" aria-hidden="true" />
          <span className="brand-sub mono">ONE PHYSICAL NEXT STEP</span>
        </div>
        <div className="topbar-status mono">
          <span className="status-chip is-offline">
            <i className="status-dot" aria-hidden="true" />
            ENGINE // LINKING
          </span>
        </div>
      </header>

      <main className="focus-wrap">
        <div className="focus-column">
          <section className="focus-card" aria-label="Loading current task">
            <div className="skel skel-head" />
            <div className="skel skel-label" />
            <div className="skel skel-step" />
            <div className="skel skel-step-short" />

            <div className="skel-meta">
              <span className="skel skel-pill" />
            </div>

            <div className="skel-actions">
              <span className="skel skel-btn" />
              <span className="skel skel-btn" />
            </div>

            <div className="skel skel-reserve" />
          </section>

          <div className="skel-composer" aria-hidden="true">
            <span className="skel skel-line" />
            <span className="skel skel-line is-short" />
          </div>
        </div>
      </main>

      <footer className="footbar mono">
        <span className="footbar-item">
          <i className="foot-dot" aria-hidden="true" />
          NEVER SHOW THE MOUNTAIN
        </span>
        <span className="footbar-item">LOADING</span>
      </footer>
    </div>
  );
}
