import { OccupiedTablesPanel } from "@/components/OccupiedTablesPanel";
import { TableCountSettings } from "@/components/TableCountSettings";

export default function MesasPage() {
  return (
    <>
      <TableCountSettings />
      <OccupiedTablesPanel />
    </>
  );
}
