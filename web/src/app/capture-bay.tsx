"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type Props = {
  apiUrl: string;
  phone: string;
  live: boolean;
};

type Filed = {
  id: number;
  activated: boolean;
  reserve: number;
  /** How many tasks this one message actually filed. */
  count: number;
  /** Who wrote the step: the person, the model, the verbatim fallback, or nobody. */
  stepSource: "user" | "engine" | "heuristic" | "none";
};

/**
 * The last receipt lives outside React on purpose.
 *
 * Filing into an empty surface swaps the card from standby to a task, and
 * the server refresh that follows remounts this whole subtree — component
 * state does not survive it. The receipt is the engine's reply to the
 * message just sent, so it has to outlive that remount. A module variable
 * does, and it resets on a real page load, which is the honest lifetime
 * for a transient confirmation.
 */
let lastFiled: Filed | null = null;

/** Grows with the dump, then scrolls. Past this the composer owns the screen. */
const MAX_HEIGHT = 280;
const MAX_CHARS = 8000;
/** Below this the counter would be noise; above it, it is a real limit. */
const COUNT_FROM = 1200;

/**
 * Web capture composer.
 *
 * Deliberately not a form: it reads as a message bar docked under the card,
 * so filing feels like talking to the engine rather than filling in a
 * database. It takes a whole dump — a week of loose ends, pasted or typed
 * over several lines — and answers with the one thing to do next. The rest
 * is captured into the hidden reserve without ever being displayed.
 *
 * Enter sends. Shift+Enter is a new line, because a dump is not a command
 * line. The textarea grows to ~280px and then scrolls, so a long message
 * never pushes the card off screen.
 */
export default function CaptureBay({ apiUrl, phone, live }: Props) {
  const router = useRouter();
  const areaRef = useRef<HTMLTextAreaElement>(null);
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filed, setFiled] = useState<Filed | null>(() => lastFiled);

  // Coming back from a remount after filing: put the caret back in the
  // composer so the next dump can be typed immediately.
  useEffect(() => {
    if (lastFiled) areaRef.current?.focus();
  }, []);

  // Auto-grow: measure the content, cap at MAX_HEIGHT, then let it scroll.
  // Height is reset first so the box can also shrink after a send.
  useEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [text]);

  function onChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
    // A new message retires the previous reply.
    if (lastFiled) {
      lastFiled = null;
      setFiled(null);
    }
  }

  async function file() {
    if (!live || pending || text.trim().length === 0) return;
    setPending(true);
    setError(null);
    lastFiled = null;
    setFiled(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/tasks`, {
        method: "POST",
        headers: { "X-Phone-Number": phone, "Content-Type": "application/json" },
        // One field: the dump. The engine decides how many tasks are in it
        // and which one is shown first.
        body: JSON.stringify({ dump: text.trim() }),
        // Extraction is a model call over a long message, so this is slower
        // than an insert. Still bounded — no infinite spinner.
        signal: AbortSignal.timeout(45000),
      });
      if (res.status === 503) {
        // Nothing was filed. Say so, and keep the dump exactly where it is.
        setError(
          "NOTHING FILED — THE ENGINE COULD NOT READ THIS. YOUR DUMP IS STILL HERE.",
        );
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as {
        task: { id: number };
        activated: boolean;
        queued_backlog_count: number;
        step_source?: "user" | "engine" | "heuristic" | "none";
        filed_count?: number;
      };
      lastFiled = {
        id: data.task.id,
        activated: data.activated,
        reserve: data.queued_backlog_count,
        count: data.filed_count ?? 1,
        stepSource: data.step_source ?? "none",
      };
      setFiled(lastFiled);
      setText("");
      router.refresh();
      areaRef.current?.focus();
    } catch {
      setError(
        "NOTHING FILED — THE ENGINE DID NOT ANSWER. YOUR DUMP IS STILL HERE.",
      );
    } finally {
      setPending(false);
    }
  }

  const empty = text.trim().length === 0;

  // Enter sends, like any message bar; Shift+Enter is a line break. The
  // composing guard keeps IME input (e.g. Japanese) from submitting on the
  // keystroke that merely confirms a candidate.
  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key !== "Enter" || e.shiftKey || e.nativeEvent.isComposing) return;
    e.preventDefault();
    void file();
  }

  const serial = filed ? `#${String(filed.id).padStart(3, "0")}` : "";
  const batch = filed && filed.count > 1 ? `${filed.count} TASKS · ` : "";
  const receipt = filed
    ? filed.activated
      ? filed.stepSource === "none"
        ? `FILED · ${batch}${serial} SAVED · NO STEP YET`
        : `FILED · ${batch}${serial} IS YOUR ONE THING`
      : `FILED · ${batch}${filed.reserve} HELD IN RESERVE`
    : "";

  return (
    <section className="composer" aria-label="Capture">
      <form
        className="composer-form"
        onSubmit={(e) => {
          e.preventDefault();
          void file();
        }}
      >
        <span className="composer-prompt mono" aria-hidden="true">
          &rsaquo;
        </span>

        <div className="composer-fields">
          <label className="sr-only" htmlFor="dump">
            Dump anything
          </label>
          <textarea
            id="dump"
            ref={areaRef}
            className="composer-input composer-input-main"
            value={text}
            onChange={onChange}
            placeholder="Dump anything — a task, a mess, a whole week"
            maxLength={MAX_CHARS}
            rows={1}
            autoComplete="off"
            onKeyDown={onKeyDown}
            disabled={!live || pending}
          />
          <div className="composer-sub">
            <span className="composer-sub-glyph mono" aria-hidden="true">
              &#8627;
            </span>
            <span className="composer-hint mono">
              {pending ? "EXTRACTING" : "SHIFT+↵ NEW LINE"}
            </span>
            {text.length > COUNT_FROM && (
              <span className="composer-count mono" aria-live="polite">
                {text.length} / {MAX_CHARS}
              </span>
            )}
          </div>
        </div>

        <button
          type="submit"
          className="composer-send mono"
          aria-label="Send dump"
          disabled={!live || pending || empty}
        >
          <span className="composer-send-label">
            {pending ? "FILING" : "SEND"}
          </span>
          <span className="composer-key" aria-hidden="true">
            &#9166;
          </span>
        </button>
      </form>

      {filed && (
        <p
          className={`composer-receipt mono${
            filed.activated && filed.stepSource === "none" ? " is-partial" : ""
          }`}
          role="status"
        >
          <i className="receipt-pip" aria-hidden="true" />
          {receipt}
        </p>
      )}

      {error && (
        <p className="composer-receipt is-error mono" role="alert">
          <i className="receipt-pip" aria-hidden="true" />
          {error}
        </p>
      )}

      {!live && (
        <p className="composer-note mono">
          PREVIEW — FILING OPENS WHEN THE ENGINE ANSWERS
        </p>
      )}
    </section>
  );
}
