type FocusTask = {
  id: number;
  title: string;
  firstMicroStep: string;
  estimatedMinutes: number;
};

export type FocusPayload = {
  live: boolean;
  task: FocusTask | null;
  reserveCount: number;
};

const FALLBACK_TASK: FocusTask = {
  id: -1,
  title: "DRAFT EMAIL TO ALICE",
  firstMicroStep: "TYPE SUBJECT LINE",
  estimatedMinutes: 12,
};

const FALLBACK_PAYLOAD: FocusPayload = {
  live: false,
  task: FALLBACK_TASK,
  reserveCount: 4,
};

/** Map the FastAPI focus payload (snake_case) onto the view model. */
function toFocusPayload(raw: unknown): FocusPayload {
  if (typeof raw !== "object" || raw === null) return FALLBACK_PAYLOAD;
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
    task:
      selected === null
        ? null
        : {
            id: num(selected.id, -1),
            title: str(selected.title, FALLBACK_TASK.title),
            firstMicroStep: str(selected.first_micro_step, FALLBACK_TASK.firstMicroStep),
            estimatedMinutes: num(selected.estimated_minutes, FALLBACK_TASK.estimatedMinutes),
          },
    reserveCount: num(data.queued_backlog_count, 0),
  };
}

export function apiConfig() {
  return {
    base: process.env.NEXT_PUBLIC_API_URL ?? "",
    phone: process.env.NEXT_PUBLIC_PHONE_NUMBER ?? "demo-web-client",
  };
}

/**
 * Single-task focus payload. Fetches live data when NEXT_PUBLIC_API_URL
 * is configured; otherwise renders the offline fallback.
 */
export async function getFocus(): Promise<FocusPayload> {
  const { base, phone } = apiConfig();
  if (!base) return FALLBACK_PAYLOAD;
  try {
    const res = await fetch(`${base}/api/v1/focus`, {
      cache: "no-store",
      headers: { "X-Phone-Number": phone },
    });
    if (!res.ok) return FALLBACK_PAYLOAD;
    return toFocusPayload(await res.json());
  } catch {
    return FALLBACK_PAYLOAD;
  }
}
