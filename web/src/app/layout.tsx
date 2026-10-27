import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "1Thing — One Physical Next Step",
  description:
    "Voice-first executive gatekeeper. Never show the mountain: one physical next step, everywhere.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
