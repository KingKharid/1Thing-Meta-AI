import { createHash, timingSafeEqual } from "node:crypto";

/**
 * Control-room session, derived rather than stored.
 *
 * The cookie holds a hash of the admin key, never the key itself, and the
 * hash is salted with SECRET_KEY so a leaked cookie cannot be replayed
 * against a different deployment. Verification recomputes the hash, so
 * there is no session table and nothing to invalidate.
 */

function adminKey(): string {
  return (process.env.ADMIN_API_KEY ?? "").trim();
}

function salt(): string {
  return (process.env.SECRET_KEY || process.env.ADMIN_API_KEY || "").trim();
}

export const ADMIN_COOKIE = "onething_admin";

export function adminConfigured(): boolean {
  return adminKey().length > 0;
}

export function adminToken(): string {
  return createHash("sha256")
    .update(`onething:${adminKey()}:${salt()}`)
    .digest("hex");
}

function sameSecret(a: string, b: string): boolean {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left, right);
}

/** True when the submitted key matches the one this deployment holds. */
export function checkKey(submitted: string): boolean {
  const expected = adminKey();
  if (!expected) return false;
  return sameSecret(submitted.trim(), expected);
}

/** True when the request carries a cookie minted from the current key. */
export function isUnlocked(cookieValue: string | undefined): boolean {
  if (!adminConfigured() || !cookieValue) return false;
  return sameSecret(cookieValue, adminToken());
}
