"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ADMIN_COOKIE, adminToken, checkKey } from "./session";

/**
 * Exchange the admin key for an httpOnly cookie.
 *
 * The key is compared in constant time and never echoed back. A wrong key
 * redirects to the gate with a failure flag; the page never reveals
 * whether the key was close, only that it was not accepted.
 */
export async function unlock(formData: FormData): Promise<void> {
  const submitted = String(formData.get("key") ?? "");

  if (!checkKey(submitted)) {
    redirect("/admin?error=1");
  }

  cookies().set(ADMIN_COOKIE, adminToken(), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });

  redirect("/admin");
}
