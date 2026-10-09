import type { ReactNode } from "react";
import { SessionHeartbeat } from "@/components/SessionHeartbeat";
import { AdminShell } from "@/components/AdminShell";

export default function PanelLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <SessionHeartbeat />
      <AdminShell>{children}</AdminShell>
    </>
  );
}
