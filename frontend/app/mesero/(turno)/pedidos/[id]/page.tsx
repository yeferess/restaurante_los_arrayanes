"use client";

import { useParams } from "next/navigation";
import { OrderBuilder } from "@/components/OrderBuilder";

export default function OrderPage() {
  const params = useParams<{ id: string }>();
  return <OrderBuilder orderId={Number(params.id)} />;
}
