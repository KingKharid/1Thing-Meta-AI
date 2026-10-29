"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type Props = {
  taskId: number;
  apiUrl: string;
  phone: string;
  live: boolean;
};

/**
 * Ask the engine for the first step of a task that does not have one.
 *
 * This exists for the two honest gaps: a task filed while the model was
 * unreachable, and tasks filed before this path called the model at all.
 * If the engine still cannot answer, the button says so — the card keeps
 * admitting it has no step rather than borrowing one.
 */
export default function DeriveStep({ taskId, apiUrl, phone, live }: Props) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function derive() {
    if (!live || pending) return;
    setPending(true);
    setFailed(false);
    try {
      const res = await fetch(`${apiUrl}/api/v1/tasks/${taskId}/derive`, {
        method: "POST",
        headers: { "X-Phone-Number": phone },
        signal: AbortSignal.timeout(30000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      router.refresh();
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="derive">
      <button
        type="button"
        className="derive-btn mono"
        onClick={derive}
        disabled={!live || pending}
      >
        {pending ? "ASKING THE ENGINE" : "DERIVE STEP"}
      </button>
      {failed && (
        <p className="derive-fail mono" role="alert">
          STILL NO STEP — THE ENGINE DID NOT ANSWER
        </p>
      )}
    </div>
  );
}
