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
              ESTABLISHING LINK
            </span>
            <span className="kicker-right">SURFACE // WEB SANCTUARY</span>
          </div>

          <section className="focus-card" aria-label="Loading current task">
            <div className="skel skel-title" />
            <div className="skel skel-step" />
            <div className="skel-meta">
              <div className="skel skel-pill" />
              <div className="skel skel-pill" />
            </div>
            <div className="skel skel-reserve" />
            <div className="skel-actions">
              <div className="skel skel-btn" />
              <div className="skel skel-btn" />
              <div className="skel skel-btn" />
            </div>
            <div className="hint-block" style={{ marginTop: 26 }}>
              <div className="kv">
                <span className="kv-key">FETCH</span>
                <span className="kv-val">/api/v1/focus …</span>
              </div>
              <div className="kv">
                <span className="kv-key">AUTH</span>
                <span className="kv-val">HEADER-MVP …</span>
              </div>
              <div className="kv">
                <span className="kv-key">STATE</span>
                <span className="kv-val">HYDRATING …</span>
              </div>
            </div>
          </section>
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
