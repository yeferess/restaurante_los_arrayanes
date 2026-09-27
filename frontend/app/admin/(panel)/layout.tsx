import type { ReactNode } from "react";
import { SessionHeartbeat } from "@/components/SessionHeartbeat";

export default function PanelLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <SessionHeartbeat />
      {children}
    </>
  );
}
