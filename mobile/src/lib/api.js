/**
 * 1Thing focus API client (Expo).
 *
 * Reads EXPO_PUBLIC_API_URL / EXPO_PUBLIC_PHONE_NUMBER. Without a
 * configured backend every call falls back to offline preview data,
 * so the companion UI is operable before the API is reachable.
 */

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "";
const PHONE = process.env.EXPO_PUBLIC_PHONE_NUMBER ?? "demo-mobile-client";

export const FALLBACK_FOCUS = {
  live: false,
  task: {
    id: -1,
    title: "DRAFT EMAIL TO ALICE",
    firstMicroStep: "TYPE SUBJECT LINE",
    estimatedMinutes: 12,
  },
  reserveCount: 4,
};

function toFocusPayload(raw) {
  if (typeof raw !== "object" || raw === null) return FALLBACK_FOCUS;
  const selected =
    typeof raw.selected_task === "object" && raw.selected_task !== null
      ? raw.selected_task
      : null;
  return {
    live: true,
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

export async function fetchFocus() {
  if (!API_URL) return FALLBACK_FOCUS;
  try {
    const res = await fetch(`${API_URL}/api/v1/focus`, {
      headers: { "X-Phone-Number": PHONE },
    });
    if (!res.ok) return FALLBACK_FOCUS;
    return toFocusPayload(await res.json());
  } catch {
    return FALLBACK_FOCUS;
  }
}

export async function completeTask(taskId) {
  const res = await fetch(`${API_URL}/api/v1/tasks/${taskId}/complete`, {
    method: "POST",
    headers: { "X-Phone-Number": PHONE },
  });
  if (!res.ok) throw new Error(`complete failed: HTTP ${res.status}`);
  return res.json();
}

export async function skipTask(taskId) {
  const res = await fetch(`${API_URL}/api/v1/tasks/${taskId}/skip?mode=reserve`, {
    method: "POST",
    headers: { "X-Phone-Number": PHONE },
  });
  if (!res.ok) throw new Error(`skip failed: HTTP ${res.status}`);
  return res.json();
}
