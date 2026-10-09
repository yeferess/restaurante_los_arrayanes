"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "@/lib/api/auth";
import styles from "./MeseroShell.module.css";

const TABS = [
  { href: "/mesero/mesas", label: "Mesas", icon: "▦" },
  { href: "/mesero/pedidos", label: "Pedidos", icon: "▤" },
  { href: "/mesero/menu", label: "Menú", icon: "☰" },
];

/** Shared bottom-tab shell for every /mesero/(turno) screen — also fixes
 * /mesero having no landing page, since there's always a tab to tap. */
export function MeseroShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.push("/mesero/login");
  }

  return (
    <div className={styles.shell}>
      <div className={styles.topbar}>
        <button type="button" className={styles.logout} onClick={handleLogout}>
          Cerrar sesión
        </button>
      </div>

      <main className={styles.main}>{children}</main>

      <nav className={styles.tabbar}>
        {TABS.map((tab) => {
          const isActive = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={isActive ? `${styles.tab} ${styles.tabActive}` : styles.tab}
              aria-current={isActive ? "page" : undefined}
            >
              <span className={styles.tabIcon} aria-hidden="true">
                {tab.icon}
              </span>
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
