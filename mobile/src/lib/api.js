/**
 * 1Thing focus API client (Expo).
 *
 * Reads EXPO_PUBLIC_API_URL / EXPO_PUBLIC_PHONE_NUMBER.
 *
 * Three honest states, mirroring the web client:
 *   preview — no API configured. Standby surface, clearly badged PREVIEW.
 *   live    — the API answered.
 *   error   — the API is configured but unreachable. No task, no
 *             invented data; the surface says the engine is offline.
 */

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "";
const PHONE = process.env.EXPO_PUBLIC_PHONE_NUMBER ?? "+15550007777";
const TIMEOUT_MS = 6000;

/** The engine is not configured. Nothing is claimed about the user's data. */
export const FALLBACK_FOCUS = {
  live: false,
  mode: "preview",
  task: null,
  reserveCount: 0,
};

/** The engine is unreachable. Deliberately carries no task. */
export const OFFLINE_FOCUS = {
  live: false,
  mode: "error",
  task: null,
  reserveCount: 0,
};

function toFocusPayload(raw) {
  if (typeof raw !== "object" || raw === null) return OFFLINE_FOCUS;
  const selected =
    typeof raw.selected_task === "object" && raw.selected_task !== null
      ? raw.selected_task
      : null;
  return {
    live: true,
    mode: "live",
    task:
      selected === null
        ? null
        : {
            id: selected.id,
            title: selected.title,
            firstMicroStep: selected.first_micro_step,
            estimatedMinutes: selected.estimated_minutes,
          },
    reserveCount:
      typeof raw.queued_backlog_count === "number" ? raw.queued_backlog_count : 0,
  };
}

async function request(path, options = {}, timeoutMs = TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${API_URL}${path}`, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchFocus() {
  if (!API_URL) return FALLBACK_FOCUS;
  try {
    const res = await request("/api/v1/focus", {
      headers: { "X-Phone-Number": PHONE },
    });
    if (!res.ok) return OFFLINE_FOCUS;
    return toFocusPayload(await res.json());
  } catch {
    return OFFLINE_FOCUS;
  }
}

export async function completeTask(taskId) {
  const res = await request(`/api/v1/tasks/${taskId}/complete`, {
    method: "POST",
    headers: { "X-Phone-Number": PHONE },
  });
  if (!res.ok) throw new Error(`complete failed: HTTP ${res.status}`);
  return res.json();
}

export async function skipTask(taskId) {
  const res = await request(`/api/v1/tasks/${taskId}/skip?mode=reserve`, {
    method: "POST",
    headers: { "X-Phone-Number": PHONE },
  });
  if (!res.ok) throw new Error(`skip failed: HTTP ${res.status}`);
  return res.json();
}

/** Extraction is a model call over a long message — much slower than a read. */
const EXTRACT_TIMEOUT_MS = 45000;

/**
 * File a dump. One field, because a dump is one message.
 *
 * The engine decides how many tasks are inside it and which one is shown
 * first; everything else lands in the hidden reserve. A 503 means nothing
 * was filed, and the caller must keep the text on screen.
 */
export async function createTask({ dump }) {
  const res = await request(
    "/api/v1/tasks",
    {
      method: "POST",
      headers: { "X-Phone-Number": PHONE, "Content-Type": "application/json" },
      body: JSON.stringify({ dump }),
    },
    EXTRACT_TIMEOUT_MS
  );
  if (!res.ok) {
    const error = new Error(`create failed: HTTP ${res.status}`);
    error.status = res.status;
    throw error;
  }
  return res.json();
}
