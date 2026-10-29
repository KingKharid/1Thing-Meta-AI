type PlaneRow = { key: string; value: string; tone?: "amber" | "emerald" };
type Plane = { id: string; title: string; ok: boolean; rows: PlaneRow[] };

/**
 * Honest offline shells: structural plane identities with zeroed rows.
 * Rendered only when the backend is unreachable, always badged OFFLINE.
 * No metric here may ever carry a plausible-looking fabricated value.
 */
const OFFLINE_PLANES: Plane[] = [
  { id: "fleet", title: "01 // FLEET PLANE", ok: false, rows: [{ key: "STATUS", value: "OFFLINE", tone: "amber" }] },
  { id: "llmops", title: "02 // LLMOPS PLANE", ok: false, rows: [{ key: "STATUS", value: "OFFLINE", tone: "amber" }] },
  { id: "state", title: "03 // STATE ENGINE PLANE", ok: false, rows: [{ key: "STATUS", value: "OFFLINE", tone: "amber" }] },
  { id: "users", title: "04 // USERS 360 PLANE", ok: false, rows: [{ key: "STATUS", value: "OFFLINE", tone: "amber" }] },
  { id: "billing", title: "05 // BILLING PLANE", ok: false, rows: [{ key: "STATUS", value: "OFFLINE", tone: "amber" }] },
  { id: "security", title: "06 // SECURITY PLANE", ok: false, rows: [{ key: "STATUS", value: "OFFLINE", tone: "amber" }] },
];

type Telemetry = { planes: Plane[]; live: boolean; checkedAt: string };

function localStamp(): string {
  return new Date().toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Control-room telemetry from GET /api/v1/telemetry. Anything other than
 * a 200 with planes — no URL configured, network error, empty payload —
 * resolves to the honest OFFLINE shells, never to fabricated metrics.
 */
async function getTelemetry(): Promise<Telemetry> {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) return { planes: OFFLINE_PLANES, live: false, checkedAt: localStamp() };
  try {
    const res = await fetch(`${base}/api/v1/telemetry`, {
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) {
      return { planes: OFFLINE_PLANES, live: false, checkedAt: localStamp() };
    }
    const data = (await res.json()) as { planes?: Plane[] };
    if (!Array.isArray(data.planes) || data.planes.length === 0) {
      return { planes: OFFLINE_PLANES, live: false, checkedAt: localStamp() };
    }
    return { planes: data.planes, live: true, checkedAt: localStamp() };
  } catch {
    return { planes: OFFLINE_PLANES, live: false, checkedAt: localStamp() };
  }
}

function splitTitle(title: string, index: number) {
  const parts = title.split(" // ");
  return parts.length > 1
    ? { code: parts[0], name: parts.slice(1).join(" // ") }
    : { code: String(index + 1).padStart(2, "0"), name: title };
}

export default async function AdminPage() {
  const { planes, live, checkedAt } = await getTelemetry();
  const nominal = planes.filter((plane) => plane.ok).length;
  const attention = planes.length - nominal;

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
          {live ? (
            <span className="status-chip is-live">
              <i className="status-dot" aria-hidden="true" />
              TELEMETRY // LIVE
            </span>
          ) : (
            <span className="status-chip">
              <i className="status-dot status-dot-steady" aria-hidden="true" />
              TELEMETRY // OFFLINE
            </span>
          )}
          <span className="status-chip">
            <i className="status-dot status-dot-steady" aria-hidden="true" />
            PLANES // {planes.length}
          </span>
        </div>
      </header>

      <main className="admin-wrap">
        <div className="focus-kicker mono">
          <span className="kicker-left">
            <span className="kicker-mark" aria-hidden="true" />
            CONTROL ROOM // READ-ONLY
          </span>
          <span className="kicker-right">SURFACE // TELEMETRY</span>
        </div>

        <div className="admin-head">
          <div>
            <h1 className="admin-title">Operational Control Room</h1>
            <p className="admin-sub mono">
              {live
                ? "SIX-PLANE DENSE TELEMETRY // FLAT CARBON PANELS // 1PX HAIRLINES"
                : "BACKEND UNREACHABLE — SHOWING EMPTY STATE // NO CACHED METRICS"}
            </p>
          </div>
        </div>

        <div className="summary-rail">
          <div className="summary-cell">
            <span className="summary-key mono">PLANES</span>
            <span className="summary-val mono">{planes.length}</span>
          </div>
          <div className="summary-cell">
            <span className="summary-key mono">NOMINAL</span>
            <span
              className={`summary-val mono ${live ? "val-emerald" : "summary-val-muted"}`}
            >
              {live ? nominal : "—"}
            </span>
          </div>
          <div className="summary-cell">
            <span className="summary-key mono">ATTENTION</span>
            <span
              className={`summary-val mono ${
                live && attention > 0 ? "val-amber" : "summary-val-muted"
              }`}
            >
              {live ? attention : "—"}
            </span>
          </div>
          <div className="summary-cell">
            <span className="summary-key mono">CHECKED</span>
            <span className="summary-val summary-val-time mono">{checkedAt}</span>
          </div>
        </div>

        <div className="admin-grid">
          {planes.map((plane, index) => {
            const { code, name } = splitTitle(plane.title, index);
            return (
              <section
                key={plane.id}
                className="plane"
                aria-label={plane.title}
                data-attention={live && !plane.ok ? true : undefined}
                data-offline={!live || undefined}
                style={{ animationDelay: `${index * 45}ms` }}
              >
                <div className="plane-head">
                  <div className="plane-heading">
                    <span className="plane-index mono">{code}</span>
                    <span className="plane-title mono">{name}</span>
                  </div>
                  <span
                    className={`plane-state mono ${
                      !live ? "is-offline" : plane.ok ? "is-ok" : "is-warn"
                    }`}
                  >
                    <i
                      className={`square ${
                        !live ? "" : plane.ok ? "square-ok" : "square-warn"
                      }`}
                      aria-hidden="true"
                    />
                    {!live ? "OFFLINE" : plane.ok ? "NOMINAL" : "ATTENTION"}
                  </span>
                </div>
                <div className="plane-rows">
                  {plane.rows.map((row) => (
                    <div key={row.key} className="kv">
                      <span className="kv-key">{row.key}</span>
                      <span
                        className={`kv-val ${row.tone === "amber" ? "val-amber" : ""} ${row.tone === "emerald" ? "val-emerald" : ""}`}
                      >
                        {row.value}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      </main>

      <footer className="footbar mono">
        <span className="footbar-item">
          <i className="foot-dot" aria-hidden="true" />
          CONTROL ROOM // READ-ONLY
        </span>
        <span className="footbar-item">BUILD 1.0.0 // FASTAPI · NEXT 14</span>
      </footer>
    </div>
  );
}
