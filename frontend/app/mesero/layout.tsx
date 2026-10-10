import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

// Metadata-only layout: wraps every /mesero/* route, including
// /mesero/login (outside the (turno) group) so the PWA manifest is
// present even before the mesero logs in (006: HTTPS/PWA
// installability).
export const metadata: Metadata = {
  title: "Los Arrayanes – Mesero",
  manifest: "/manifest-mesero.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#c2541f",
};

export default function MeseroLayout({ children }: { children: ReactNode }) {
  return children;
}
