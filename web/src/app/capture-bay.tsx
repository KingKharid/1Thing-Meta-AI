"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type Props = {
  apiUrl: string;
  phone: string;
  live: boolean;
  /** The task on screen now, so a stale receipt cannot outlive it. */
  activeId: number | null;
  /** A dump to start with — used by the judge's /demo hand-off. */
  prefill?: string;
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
export default function CaptureBay({
  apiUrl,
  phone,
  live,
  activeId,
  prefill = "",
}: Props) {
  const router = useRouter();
  const areaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState(prefill);
  const [pending, setPending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filed, setFiled] = useState<Filed | null>(() => lastFiled);
  // Extraction is a 10–15s model call on a long dump. A spinner alone
  // looks frozen, so the surface counts the seconds out loud.
  const [elapsed, setElapsed] = useState(0);

  // Coming back from a remount after filing: put the caret back in the
  // composer so the next dump can be typed immediately. The demo hand-off
  // arrives with text already in the box, so the caret goes to the end.
  useEffect(() => {
    if (lastFiled || prefill) areaRef.current?.focus();
  }, [prefill]);

  useEffect(() => {
    if (!pending) {
      setElapsed(0);
      return;
    }
    const startedAt = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 500);
    return () => clearInterval(timer);
  }, [pending]);

  // A receipt is a claim about what is on screen. Once the surface moves
  // on — DONE promoted the next task — that claim is no longer true, so
  // it goes away rather than sitting there contradicting the card.
  useEffect(() => {
    if (lastFiled?.activated && lastFiled.id !== activeId) {
      lastFiled = null;
      setFiled(null);
    }
  }, [activeId]);

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
    if (!live || busy || text.trim().length === 0) return;
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
        // Extraction is a model call over a long message. Worst case is
        // two provider timeouts back to back (~40s), so the ceiling is
        // generous — but still bounded, and the surface counts seconds.
        signal: AbortSignal.timeout(90000),
      });
      if (res.status === 503) {
        // Nothing was filed. Say so, and keep the dump exactly where it is.
        setError(
          "NOTHING FILED — THE ENGINE COULD NOT READ THIS. YOUR DUMP IS STILL HERE. PRESS SEND TO RETRY.",
        );
        return;
      }
      if (res.status === 400) {
        // A refusal, not an outage: greeting dumps and blank titles land
        // here. The server's detail says why; surface it, keep the text.
        const detail = await readDetail(res);
        setError(detail ?? "NOTHING FILED — THAT WAS NOT ACCEPTED.");
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
        "NOTHING FILED — THE ENGINE DID NOT ANSWER. YOUR DUMP IS STILL HERE. PRESS SEND TO RETRY.",
      );
    } finally {
      setPending(false);
    }
  }

  const empty = text.trim().length === 0;
  const busy = pending || uploading;

  // Server refusals carry a plain detail string ("That looks like a
  // greeting…"). Anything else falls back to the generic nothing-filed
  // line so an unreadable error never renders raw JSON.
  async function readDetail(res: Response): Promise<string | null> {
    try {
      const data = (await res.json()) as { detail?: unknown };
      if (typeof data.detail === "string" && data.detail.trim()) {
        return data.detail.trim().toUpperCase();
      }
    } catch {
      // Fall through to the generic line below.
    }
    return null;
  }

  // Photo or voice memo: same pipeline WhatsApp media takes, same
  // receipt shape back. The file input (not a drop zone) is the whole
  // UI — on phones it opens camera, gallery, or recorder directly.
  async function attach(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0];
    e.target.value = "";
    if (!live || busy || !picked) return;
    setUploading(true);
    setError(null);
    lastFiled = null;
    setFiled(null);
    try {
      const form = new FormData();
      form.append("file", picked);
      const res = await fetch(`${apiUrl}/api/v1/tasks/media`, {
        method: "POST",
        headers: { "X-Phone-Number": phone },
        body: form,
        signal: AbortSignal.timeout(120000),
      });
      if (res.status === 503) {
        setError(
          "NOTHING FILED — THE FILE COULD NOT BE READ. NOTHING WAS LOST.",
        );
        return;
      }
      if (res.status === 400) {
        const detail = await readDetail(res);
        setError(detail ?? "NOTHING FILED — THAT FILE WAS NOT ACCEPTED.");
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
      router.refresh();
      areaRef.current?.focus();
    } catch {
      setError("NOTHING FILED — THE FILE DID NOT SEND. NOTHING WAS LOST.");
    } finally {
      setUploading(false);
    }
  }

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
  const hint = pending
    ? `EXTRACTING · ${elapsed}S`
    : uploading
      ? "READING FILE"
      : "SHIFT+↵ NEW LINE";

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
              {hint}
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
          disabled={!live || busy || empty}
        >
          <span className="composer-send-label">
            {pending || uploading ? "FILING" : "SEND"}
          </span>
          <span className="composer-key" aria-hidden="true">
            &#9166;
          </span>
        </button>

        {/* Photo or voice memo. The native file input is the whole UI:
            on phones it opens camera, gallery, or recorder directly. */}
        <input
          ref={fileRef}
          type="file"
          accept="image/*,audio/*"
          className="sr-only"
          aria-label="Attach a photo or voice note"
          disabled={!live || busy}
          onChange={(e) => void attach(e)}
        />
        <button
          type="button"
          className="composer-attach mono"
          aria-label="Attach a photo or voice note"
          disabled={!live || busy}
          onClick={() => fileRef.current?.click()}
        >
          <span className="composer-attach-mark" aria-hidden="true" />
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
