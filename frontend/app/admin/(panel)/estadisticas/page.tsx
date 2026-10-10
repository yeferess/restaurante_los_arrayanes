import { DaySummaryPanel } from "@/components/DaySummaryPanel";
import { DateRangeFilter } from "@/components/DateRangeFilter";
import { DayMovementView } from "@/components/DayMovementView";

export default function EstadisticasPage() {
  return (
    <>
      <DaySummaryPanel />
      <DateRangeFilter />
      <DayMovementView />
    </>
  );
}
