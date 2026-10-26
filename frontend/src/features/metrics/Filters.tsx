import { useCatalog } from "@/api/hooks";
import { Segmented } from "@/components/ui/Segmented";
import { PRESETS, type usePeriod } from "./usePeriod";

export function Filters({ period }: { period: ReturnType<typeof usePeriod> }) {
  const catalog = useCatalog();
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Segmented
        label="Período"
        options={PRESETS}
        value={period.preset}
        onChange={period.setPreset}
      />
      <label className="sr-only" htmlFor="area-filter">
        Área
      </label>
      <select
        id="area-filter"
        className="h-11 w-52 rounded-full bg-surface px-4 text-sm shadow-xs ring-1 ring-line outline-none ring-inset focus:ring-2 focus:ring-ink"
        value={period.areaId ?? ""}
        onChange={(e) => period.setArea(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">Todas las áreas</option>
        {catalog.data?.areas.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
    </div>
  );
}
