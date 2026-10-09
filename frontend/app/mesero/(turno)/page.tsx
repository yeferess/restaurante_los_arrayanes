"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function MeseroIndexPage() {
  const router = useRouter();
  useEffect(() => {
    router.push("/mesero/mesas");
  }, [router]);
  return null;
}
