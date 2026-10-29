type FocusTask = {
  id: number;
  title: string;
  firstMicroStep: string;
  estimatedMinutes: number;
};

/**
 * `preview` = no API configured. `error` = API configured but unreachable.
 *
 * Both are honest empty states. Neither carries a task: a demo task on a
 * live-looking surface is indistinguishable from a real one, which is how
 * a placeholder step once showed up under a real dump.
 */
export type FocusMode = "live" | "preview" | "error";

export type FocusPayload = {
  live: boolean;
  mode: FocusMode;
  task: FocusTask | null;
  reserveCount: number;
  /** ISO timestamp of the fetch, so the UI can show an honest "updated" line. */
  updatedAt: string;
};

function emptyPayload(mode: FocusMode): FocusPayload {
  return {
    live: false,
    mode,
    task: null,
    reserveCount: 0,
    updatedAt: new Date().toISOString(),
  };
}

function previewPayload(): FocusPayload {
  return emptyPayload("preview");
}

function errorPayload(): FocusPayload {
  return emptyPayload("error");
}

/** Map the FastAPI focus payload (snake_case) onto the view model. */
function toFocusPayload(raw: unknown): FocusPayload {
  if (typeof raw !== "object" || raw === null) return errorPayload();
  const data = raw as Record<string, unknown>;
  const selected =
    typeof data.selected_task === "object" && data.selected_task !== null
      ? (data.selected_task as Record<string, unknown>)
      : null;
  const str = (value: unknown, fallback: string) =>
    typeof value === "string" && value.length > 0 ? value : fallback;
  const num = (value: unknown, fallback: number) =>
    typeof value === "number" && Number.isFinite(value) ? value : fallback;
  return {
    live: true,
    mode: "live",
    task:
      selected === null
        ? null
        : {
            id: num(selected.id, -1),
            title: str(selected.title, "UNTITLED"),
            // An empty step stays empty. The card says so; it does not
            // borrow a placeholder from a demo.
            firstMicroStep: str(selected.first_micro_step, ""),
            estimatedMinutes: num(selected.estimated_minutes, 15),
          },
    reserveCount: num(data.queued_backlog_count, 0),
    updatedAt: new Date().toISOString(),
  };
}

export function apiConfig() {
  return {
    base: process.env.NEXT_PUBLIC_API_URL ?? "",
    phone: process.env.NEXT_PUBLIC_PHONE_NUMBER ?? "+15550007777",
    whatsapp: process.env.NEXT_PUBLIC_WHATSAPP_NUMBER ?? "",
  };
}

/**
 * Single-task focus payload. Fetches live data when NEXT_PUBLIC_API_URL
 * is configured; otherwise renders the offline preview. A failed fetch
 * is reported as an error state, never disguised as a real task.
 */
export async function getFocus(): Promise<FocusPayload> {
  const { base, phone } = apiConfig();
  if (!base) return previewPayload();
  try {
    const res = await fetch(`${base}/api/v1/focus`, {
      cache: "no-store",
      headers: { "X-Phone-Number": phone },
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) return errorPayload();
    return toFocusPayload(await res.json());
  } catch {
    return errorPayload();
  }
}
