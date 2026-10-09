"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "@/lib/api/auth";
import styles from "./AdminShell.module.css";

const SECTIONS: Array<{ label: string; items: Array<{ href: string; label: string }> }> = [
  { label: "", items: [{ href: "/admin/mesas", label: "Mesas" }] },
  {
    label: "Menú",
    items: [
      { href: "/admin/menu/categorias", label: "Categorías" },
      { href: "/admin/menu/productos", label: "Productos" },
      { href: "/admin/menu/cuentas", label: "Cuentas" },
    ],
  },
  {
    label: "Personal",
    items: [
      { href: "/admin/usuarios/admins", label: "Admins" },
      { href: "/admin/usuarios/meseros", label: "Meseros" },
    ],
  },
  { label: "", items: [{ href: "/admin/pedidos", label: "Pedidos" }] },
];

/** Shared nav shell for every /admin/(panel) screen: sidebar with every
 * section (also fixes /admin having no landing page — there's always
 * somewhere to click) plus a logout control, which didn't exist anywhere
 * before this. */
export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.push("/admin/login");
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>Los Arrayanes</div>
        {SECTIONS.map((section) => (
          <div className={styles.group} key={section.label || section.items[0].href}>
            {section.label && <span className={styles.groupLabel}>{section.label}</span>}
            <nav className={styles.nav}>
              {section.items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={isActive ? `${styles.link} ${styles.linkActive}` : styles.link}
                    aria-current={isActive ? "page" : undefined}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}
        <div className={styles.spacer} />
        <button type="button" className={styles.logout} onClick={handleLogout}>
          Cerrar sesión
        </button>
      </aside>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
