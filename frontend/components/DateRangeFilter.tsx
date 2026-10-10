"use client";

import { useState, type FormEvent } from "react";
import { getRangeSummary, type RangeSummary, type ApiErrorBody } from "@/lib/api/stats";
import { formatPrice } from "@/lib/format";
import { StatsSummaryBreakdown } from "./StatsSummaryBreakdown";
import styles from "./DateRangeFilter.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** Date-range filter (006-estadisticas, RF-5): same breakdown as the
 * day summary, for an arbitrary from/to range. */
export function DateRangeFilter() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [summary, setSummary] = useState<RangeSummary | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      setSummary(await getRangeSummary(from, to));
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section className={styles.section}>
      <h1 className={styles.heading}>Rango de fechas</h1>
      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="range-from">
            Desde
          </label>
          <input
            id="range-from"
            type="date"
            className={styles.input}
            value={from}
            onChange={(event) => setFrom(event.target.value)}
            required
          />
        </div>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="range-to">
            Hasta
          </label>
          <input
            id="range-to"
            type="date"
            className={styles.input}
            value={to}
            onChange={(event) => setTo(event.target.value)}
            required
          />
        </div>
        <button type="submit" className={styles.submitButton}>
          Consultar
        </button>
      </form>

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
              <span className={styles.totalLabel}>Pedidos enviados</span>
              <span className={styles.totalValue}>
                {summary.orders_sent_count}
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
