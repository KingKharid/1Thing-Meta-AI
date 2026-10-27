"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Props = {
  taskId: number;
  apiUrl: string;
  phone: string;
  live: boolean;
};

function IconCheck() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M3.5 8.4 6.4 11.3 12.5 4.7" />
    </svg>
  );
}

function IconSkip() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M3 8h9M8.6 4.6 12 8l-3.4 3.4" />
    </svg>
  );
}

function IconBreak() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M3 4h10M3 8h7M3 12h4" />
    </svg>
  );
}

export default function FocusActions({ taskId, apiUrl, phone, live }: Props) {
  const router = useRouter();
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const post = useCallback(
    async (path: string, label: string) => {
      if (!live) {
        setError("OFFLINE PREVIEW — ACTIONS DISABLED");
        return;
      }
      setPending(label);
      setError(null);
      try {
        const res = await fetch(`${apiUrl}${path}`, {
          method: "POST",
          headers: { "X-Phone-Number": phone },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        router.refresh();
      } catch {
        setError(`${label} FAILED — RETRY`);
      } finally {
        setPending(null);
      }
    },
    [apiUrl, phone, live, router]
  );

  // Elite-product touch: D completes, S skips. No inputs on this surface,
  // so bare keys are unambiguous. Modifiers and repeats never fire.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.repeat || e.metaKey || e.ctrlKey || e.altKey || pending !== null) return;
      const key = e.key.toLowerCase();
      if (key === "d") post(`/api/v1/tasks/${taskId}/complete`, "DONE");
      else if (key === "s") post(`/api/v1/tasks/${taskId}/skip?mode=reserve`, "SKIP");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [post, taskId, pending]);

  return (
    <div>
      <div className="actions">
        <button
          type="button"
          className="btn btn-done"
          aria-label="Mark done (keyboard: D)"
          aria-busy={pending === "DONE"}
          data-pending={pending === "DONE" || undefined}
          disabled={pending !== null}
          onClick={() => post(`/api/v1/tasks/${taskId}/complete`, "DONE")}
        >
          {pending === "DONE" ? (
            <span className="btn-busy">
              <span className="spinner" aria-hidden="true" />
              DONE
            </span>
          ) : (
            <>
              <IconCheck />
              <span>DONE</span>
              {live && <kbd>D</kbd>}
            </>
          )}
        </button>
        <button
          type="button"
          className="btn btn-skip"
          aria-label="Skip task (keyboard: S)"
          aria-busy={pending === "SKIP"}
          data-pending={pending === "SKIP" || undefined}
          disabled={pending !== null}
          onClick={() => post(`/api/v1/tasks/${taskId}/skip?mode=reserve`, "SKIP")}
        >
          {pending === "SKIP" ? (
            <span className="btn-busy">
              <span className="spinner" aria-hidden="true" />
              SKIP
            </span>
          ) : (
            <>
              <IconSkip />
              <span>SKIP</span>
              {live && <kbd>S</kbd>}
            </>
          )}
        </button>
        <button
          type="button"
          className="btn btn-chunk"
          aria-label="Break down task (coming soon)"
          disabled
          title="Chunking lands with the breakdown API"
        >
          <IconBreak />
          <span>CHUNK</span>
          <span className="tag">SOON</span>
        </button>
      </div>
      {error && (
        <div className="form-error mono" role="alert">
          <span className="form-error-mark" aria-hidden="true">
            !
          </span>
          {error}
        </div>
      )}
    </div>
  );
}
