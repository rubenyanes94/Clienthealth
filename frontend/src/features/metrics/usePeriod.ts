import { useSearchParams } from "react-router";
import { TIMEZONE } from "@/lib/format";

export type Preset = "today" | "7d" | "30d" | "month";

export const PRESETS: { value: Preset; label: string }[] = [
  { value: "today", label: "Hoy" },
  { value: "7d", label: "7 días" },
  { value: "30d", label: "30 días" },
  { value: "month", label: "Este mes" },
];

const isoDay = new Intl.DateTimeFormat("en-CA", { timeZone: TIMEZONE });

function shift(day: string, days: number): string {
  const d = new Date(`${day}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function rangeFor(preset: Preset, now = new Date()): { from: string; to: string } {
  const today = isoDay.format(now);
  switch (preset) {
    case "today":
      return { from: today, to: today };
    case "7d":
      return { from: shift(today, -6), to: today };
    case "30d":
      return { from: shift(today, -29), to: today };
    case "month":
      return { from: `${today.slice(0, 8)}01`, to: today };
  }
}

/** Período y área de los paneles, guardados en la URL para poder compartir el enlace. */
export function usePeriod() {
  const [search, setSearch] = useSearchParams();
  const preset = (PRESETS.find((p) => p.value === search.get("periodo"))?.value ?? "7d") as Preset;
  const areaParam = search.get("area");
  const areaId = areaParam ? Number(areaParam) : null;
  const { from, to } = rangeFor(preset);

  const update = (next: { preset?: Preset; areaId?: number | null }) => {
    const params = new URLSearchParams(search);
    if (next.preset) params.set("periodo", next.preset);
    if (next.areaId !== undefined) {
      if (next.areaId === null) params.delete("area");
      else params.set("area", String(next.areaId));
    }
    setSearch(params, { replace: true });
  };

  return {
    preset,
    areaId,
    query: { from, to, ...(areaId !== null ? { area_id: areaId } : {}) },
    setPreset: (p: Preset) => update({ preset: p }),
    setArea: (id: number | null) => update({ areaId: id }),
  };
}
