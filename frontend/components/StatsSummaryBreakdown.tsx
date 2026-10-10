import {
  type MoneyByAccount,
  type OrdersByWaiter,
  type TopProduct,
} from "@/lib/api/stats";
import { formatPrice } from "@/lib/format";
import styles from "./StatsSummaryBreakdown.module.css";

/** Shared breakdown rendering (006-estadisticas, RF-2/3/4), reused by
 * both the single-day and the date-range views. */
export function StatsSummaryBreakdown({
  moneyByAccount,
  ordersByWaiter,
  topProducts,
}: {
  moneyByAccount: MoneyByAccount[];
  ordersByWaiter: OrdersByWaiter[];
  topProducts: TopProduct[];
}) {
  return (
    <div className={styles.grid}>
      <section className={styles.card}>
        <h2 className={styles.cardHeading}>Dinero por cuenta</h2>
        {moneyByAccount.length === 0 ? (
          <p className={styles.empty}>Sin datos.</p>
        ) : (
          <ul className={styles.list}>
            {moneyByAccount.map((row) => (
              <li key={row.account_name} className={styles.row}>
                <span>{row.account_name}</span>
                <span className={styles.value}>${formatPrice(row.total)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={styles.card}>
        <h2 className={styles.cardHeading}>Pedidos por mesero</h2>
        {ordersByWaiter.length === 0 ? (
          <p className={styles.empty}>Sin datos.</p>
        ) : (
          <ul className={styles.list}>
            {ordersByWaiter.map((row) => (
              <li key={row.waiter_username} className={styles.row}>
                <span>{row.waiter_username}</span>
                <span className={styles.value}>{row.orders_sent}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={styles.card}>
        <h2 className={styles.cardHeading}>Productos más vendidos</h2>
        {topProducts.length === 0 ? (
          <p className={styles.empty}>Sin datos.</p>
        ) : (
          <ol className={styles.list}>
            {topProducts.map((row) => (
              <li key={row.product_name} className={styles.row}>
                <span>{row.product_name}</span>
                <span className={styles.value}>{row.quantity}</span>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
