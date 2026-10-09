import { LoginFormMesero } from "@/components/LoginFormMesero";
import styles from "./page.module.css";

export default function MeseroLoginPage() {
  return (
    <main className={styles.main}>
      <h1 className={styles.heading}>Turno de mesero</h1>
      <LoginFormMesero />
    </main>
  );
}
