import { unlock } from "./actions";
import { adminConfigured } from "./session";

/**
 * The control room is operator-only, so it asks for the key before it
 * renders a single row. When the deployment has no key configured the
 * gate says so instead of pretending the form would work.
 */
export default function AdminGate({ failed }: { failed: boolean }) {
  const configured = adminConfigured();

  return (
    <div className="shell grid-overlay">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <a className="wordmark" href="/">
            1Thing
          </a>
          <span className="brand-rule" aria-hidden="true" />
          <span className="brand-sub mono">CONTROL ROOM</span>
        </div>
        <div className="topbar-status mono">
          <span className="status-chip">
            <i className="status-dot" aria-hidden="true" />
            OPERATOR ONLY
          </span>
        </div>
      </header>

      <main className="focus-wrap">
        <div className="focus-column">
          <section className="focus-card focus-card-idle" aria-label="Admin unlock">
            <div className="focus-head">
              <span className="focus-task mono">SIX-PLANE TELEMETRY</span>
            </div>

            <h1 className="focus-title">OPERATOR KEY REQUIRED</h1>
            <p className="focus-sub">
              Every row behind this gate is measured live from the running
              system. It is not a public page.
            </p>

            {!configured ? (
              <p className="composer-receipt is-error mono" role="alert">
                <i className="receipt-pip" aria-hidden="true" />
                ADMIN_API_KEY IS NOT CONFIGURED ON THIS DEPLOYMENT
              </p>
            ) : (
              <form action={unlock} className="admin-gate-form">
                <label className="admin-gate-label mono" htmlFor="key">
                  X-ADMIN-KEY
                </label>
                <input
                  id="key"
                  name="key"
                  type="password"
                  autoComplete="off"
                  autoFocus
                  required
                  className="admin-gate-input mono"
                  aria-describedby="admin-gate-hint"
                />
                <button type="submit" className="ingest-cta mono">
                  UNLOCK <span aria-hidden="true">→</span>
                </button>
                <p id="admin-gate-hint" className="composer-note mono">
                  SENT AS X-ADMIN-KEY. NEVER STORED IN THE BROWSER.
                </p>
              </form>
            )}

            {failed && configured && (
              <p className="composer-receipt is-error mono" role="alert">
                <i className="receipt-pip" aria-hidden="true" />
                THAT KEY WAS NOT ACCEPTED
              </p>
            )}
          </section>
        </div>
      </main>

      <footer className="footbar mono">
        <span className="footbar-item">
          <i className="foot-dot" aria-hidden="true" />
          NEVER SHOW THE MOUNTAIN
        </span>
        <a className="footbar-link mono" href="/">
          BACK TO THE SANCTUARY <span aria-hidden="true">→</span>
        </a>
      </footer>
    </div>
  );
}
