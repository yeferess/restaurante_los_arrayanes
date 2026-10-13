"use client";

import { useParams } from "next/navigation";
import { OrderBuilder } from "@/components/OrderBuilder";

/** 003 RF-18: the admin builds their own order with the waiters' screen. */
export default function AdminOrderPage() {
  const params = useParams<{ id: string }>();
  return <OrderBuilder orderId={Number(params.id)} />;
}
