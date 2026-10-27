"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Props = {
  taskId: number;
  apiUrl: string;
  phone: string;
  live: boolean;
};

export default function FocusActions({ taskId, apiUrl, phone, live }: Props) {
  const router = useRouter();
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function post(path: string, label: string) {
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
  }

  return (
    <div>
      <div className="actions">
        <button
          type="button"
          className="btn btn-done"
          aria-label="Mark done"
          disabled={pending !== null}
          onClick={() => post(`/api/v1/tasks/${taskId}/complete`, "DONE")}
        >
          {pending === "DONE" ? "..." : "DONE"}
        </button>
        <button
          type="button"
          className="btn btn-skip"
          aria-label="Skip task"
          disabled={pending !== null}
          onClick={() => post(`/api/v1/tasks/${taskId}/skip?mode=reserve`, "SKIP")}
        >
          {pending === "SKIP" ? "..." : "SKIP"}
        </button>
        <button
          type="button"
          className="btn btn-chunk"
          aria-label="Break down task (coming soon)"
          disabled
          title="Chunking lands with the breakdown API"
        >
          CHUNK
        </button>
      </div>
      {error && (
        <div className="mono" role="alert" style={{ color: "var(--amber)", marginTop: 16 }}>
          {error}
        </div>
      )}
    </div>
  );
}
