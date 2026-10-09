import type { ReactNode } from "react";
import { MeseroShell } from "@/components/MeseroShell";

// No heartbeat needed here: a mesero session never expires from
// inactivity (RF-9, specs/001-autenticacion-usuarios/spec.md) — unlike
// admin/(panel), which mounts SessionHeartbeat (RF-8). Route protection
// itself lives in proxy.ts, not in this layout.
export default function TurnoLayout({ children }: { children: ReactNode }) {
  return <MeseroShell>{children}</MeseroShell>;
}
