"use client";

import { useEffect, useState } from "react";
import { getDaySummary, type DaySummary, type ApiErrorBody } from "@/lib/api/stats";
import { formatPrice } from "@/lib/format";
import { StatsSummaryBreakdown } from "./StatsSummaryBreakdown";
import styles from "./DaySummaryPanel.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** Day summary panel (006-estadisticas, RF-1 a RF-4): money collected,
 * breakdown by account/waiter/product for a single day — today by
 * default. */
export function DaySummaryPanel() {
  const [date, setDate] = useState("");
  const [summary, setSummary] = useState<DaySummary | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setMessage(null);
    getDaySummary(date || undefined)
      .then(setSummary)
      .catch((error) => setMessage(formatError(error)));
  }, [date]);

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <h1 className={styles.heading}>Resumen del día</h1>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="day-summary-date">
            Fecha
          </label>
          <input
            id="day-summary-date"
            type="date"
            className={styles.input}
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
        </div>
      </div>

      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}

      {summary && (
        <>
          <div className={styles.totals}>
            <div className={styles.totalCard}>
              <span className={styles.totalLabel}>Dinero cobrado</span>
              <span className={styles.totalValue}>
                ${formatPrice(summary.money_total)}
              </span>
            </div>
            <div className={styles.totalCard}>
              <span className={styles.totalLabel}>Pedidos cobrados</span>
              <span className={styles.totalValue}>
                {summary.orders_charged_count}
              </span>
            </div>
          </div>

          <StatsSummaryBreakdown
            moneyByAccount={summary.money_by_account}
            ordersByWaiter={summary.orders_by_waiter}
            topProducts={summary.top_products}
          />
        </>
      )}
    </section>
  );
}
