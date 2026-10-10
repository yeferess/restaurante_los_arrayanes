import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

// Metadata-only layout: wraps every /admin/* route, including
// /admin/login (outside the (panel) group) so the PWA manifest is
// present even before the admin logs in (006: HTTPS/PWA
// installability).
export const metadata: Metadata = {
  title: "Los Arrayanes – Admin",
  manifest: "/manifest-admin.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#171717",
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  return children;
}
