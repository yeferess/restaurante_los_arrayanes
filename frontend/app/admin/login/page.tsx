import { LoginFormAdmin } from "@/components/LoginFormAdmin";
import styles from "./page.module.css";

export default function AdminLoginPage() {
  return (
    <main className={styles.main}>
      <h1 className={styles.heading}>Panel de administración</h1>
      <LoginFormAdmin />
    </main>
  );
}
