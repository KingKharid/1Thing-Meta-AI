type PlaneRow = { key: string; value: string; tone?: "amber" | "emerald" };
type Plane = { id: string; title: string; ok: boolean; rows: PlaneRow[] };

const FALLBACK_PLANES: Plane[] = [
  {
    id: "fleet",
    title: "01 // FLEET PLANE",
    ok: true,
    rows: [
      { key: "API PING", value: "18MS" },
      { key: "DB POOL", value: "4/20 IDLE" },
      { key: "REDIS", value: "CONNECTED" },
      { key: "UPTIME", value: "99.98%" },
    ],
  },
  {
    id: "llmops",
    title: "02 // LLMOPS PLANE",
    ok: true,
    rows: [
      { key: "META TOKENS", value: "41.2K / 2M", tone: "amber" },
      { key: "BASETEN TPM", value: "0.8M / 2M" },
      { key: "TRANSCRIBE", value: "132 CALLS" },
      { key: "COST TO DATE", value: "$18.40" },
    ],
  },
  {
    id: "state",
    title: "03 // STATE ENGINE PLANE",
    ok: true,
    rows: [
      { key: "ACTIVE TASKS", value: "1,204", tone: "emerald" },
      { key: "INVARIANT TRIPS", value: "0" },
      { key: "DEMOTIONS", value: "312" },
      { key: "SWEEPS", value: "LAST 00:00 OK" },
    ],
  },
  {
    id: "users",
    title: "04 // USERS 360 PLANE",
    ok: true,
    rows: [
      { key: "FOCUS SESSIONS", value: "866 LIVE" },
      { key: "AVG STREAK", value: "6.2 DAYS" },
      { key: "MOMENTUM P50", value: "74" },
      { key: "D7 RETENTION", value: "41%" },
    ],
  },
  {
    id: "billing",
    title: "05 // BILLING PLANE",
    ok: true,
    rows: [
      { key: "MRR", value: "$12,480" },
      { key: "ZERO-LOGIN SUBS", value: "1,038" },
      { key: "WEBHOOKS", value: "0 FAILED" },
      { key: "TRIALS", value: "214" },
    ],
  },
  {
    id: "security",
    title: "06 // SECURITY PLANE",
    ok: false,
    rows: [
      { key: "WA HANDSHAKES", value: "1,204 OK" },
      { key: "RATE LIMITS", value: "3 TRIPPED", tone: "amber" },
      { key: "OTP FAILURES", value: "11 / 24H" },
      { key: "AUDIT LOG", value: "SEALED" },
    ],
  },
];

/**
 * Control-room telemetry. Lives behind NEXT_PUBLIC_API_URL so the room
 * renders offline (fallback) until the telemetry endpoint lands.
 */
async function getPlanes(): Promise<Plane[]> {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) return FALLBACK_PLANES;
  try {
    const res = await fetch(`${base}/api/v1/telemetry`, { cache: "no-store" });
    if (!res.ok) return FALLBACK_PLANES;
    const data = (await res.json()) as { planes?: Plane[] };
    return Array.isArray(data.planes) && data.planes.length > 0
      ? data.planes
      : FALLBACK_PLANES;
  } catch {
    return FALLBACK_PLANES;
  }
}

function splitTitle(title: string, index: number) {
  const parts = title.split(" // ");
  return parts.length > 1
    ? { code: parts[0], name: parts.slice(1).join(" // ") }
    : { code: String(index + 1).padStart(2, "0"), name: title };
}

export default async function AdminPage() {
  const planes = await getPlanes();
  const nominal = planes.filter((plane) => plane.ok).length;
  const attention = planes.length - nominal;
  const signals = planes.reduce((total, plane) => total + plane.rows.length, 0);

  return (
    <div className="shell grid-overlay">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="wordmark">1Thing</span>
          <span className="brand-rule" aria-hidden="true" />
          <span className="brand-sub mono">CONTROL ROOM</span>
        </div>
        <div className="topbar-status mono">
          <span className="status-chip is-live">
            <i className="status-dot" aria-hidden="true" />
            TELEMETRY // LIVE
          </span>
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
              SIX-PLANE DENSE TELEMETRY // FLAT CARBON PANELS // 1PX HAIRLINES
            </p>
          </div>
          <div className="admin-legend mono">
            <span>
              <i className="square square-ok" aria-hidden="true" />
              NOMINAL
            </span>
            <span>
              <i className="square square-warn" aria-hidden="true" />
              ATTENTION
            </span>
          </div>
        </div>

        <div className="summary-rail">
          <div className="summary-cell">
            <span className="summary-key mono">PLANES</span>
            <span className="summary-val mono">{planes.length}</span>
          </div>
          <div className="summary-cell">
            <span className="summary-key mono">NOMINAL</span>
            <span className="summary-val mono val-emerald">{nominal}</span>
          </div>
          <div className="summary-cell">
            <span className="summary-key mono">ATTENTION</span>
            <span className={`summary-val mono ${attention > 0 ? "val-amber" : ""}`}>
              {attention}
            </span>
          </div>
          <div className="summary-cell">
            <span className="summary-key mono">SIGNALS</span>
            <span className="summary-val mono">{signals}</span>
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
                style={{ animationDelay: `${index * 45}ms` }}
              >
                <div className="plane-head">
                  <div className="plane-heading">
                    <span className="plane-index mono">{code}</span>
                    <span className="plane-title mono">{name}</span>
                  </div>
                  <span className={`plane-state mono ${plane.ok ? "is-ok" : "is-warn"}`}>
                    <i
                      className={`square ${plane.ok ? "square-ok" : "square-warn"}`}
                      aria-hidden="true"
                    />
                    {plane.ok ? "NOMINAL" : "ATTENTION"}
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
        <span className="footbar-item">MUTATIONS REQUIRE PHASE-4 KEYS</span>
      </footer>
    </div>
  );
}
