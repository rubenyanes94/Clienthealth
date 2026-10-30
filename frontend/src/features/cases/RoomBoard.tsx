import clsx from "clsx";
import type { CaseStage, CasesLive } from "@/api/types";
import { formatElapsed } from "@/lib/format";
import { useNow } from "@/lib/useNow";
import { STAGE_LABEL } from "./stages";

const LIVE_STAGES: Exclude<CaseStage, "closed">[] = [
  "registered",
  "in_progress",
  "waiting",
  "resolved",
];

function minutes(value: number | null): string {
  if (value === null) return "—";
  return value < 60
    ? `${Math.round(value)} min`
    : `${Math.floor(value / 60)} h ${Math.round(value % 60)} min`;
}

/** Situación de la sala en tiempo real. Tocar una etapa o un área filtra la lista de abajo. */
export function RoomBoard({
  live,
  stage,
  areaId,
  onStage,
  onArea,
}: {
  live: CasesLive;
  stage: string;
  areaId: number | null;
  onStage: (stage: CaseStage | "open") => void;
  onArea: (areaId: number | null) => void;
}) {
  const now = useNow();
  return (
    <section aria-label="Sala ahora" className="mb-4">
      <div className="rounded-3xl bg-ink p-5 text-white shadow-pop sm:p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <span className="size-2 animate-pulse rounded-full bg-green-400" aria-hidden /> Sala
            ahora
          </h2>
          <p className="text-xs text-white/60">
            Hoy: {live.created_today} creados · {live.closed_today} cerrados · 1ª atención{" "}
            {minutes(live.first_attention_median)} · resolución {minutes(live.resolution_median)}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {LIVE_STAGES.map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={stage === s}
              onClick={() => onStage(stage === s ? "open" : s)}
              className={clsx(
                "rounded-2xl px-4 py-3 text-left transition active:scale-[0.98]",
                stage === s ? "bg-white text-ink" : "bg-white/10 hover:bg-white/20",
              )}
            >
              <div className={clsx("text-xs", stage === s ? "text-ink-3" : "text-white/60")}>
                {STAGE_LABEL[s]}
              </div>
              <div className="mt-1 text-3xl font-bold tabular-nums">{live[s]}</div>
            </button>
          ))}
          <div
            className={clsx(
              "rounded-2xl px-4 py-3",
              live.late > 0 ? "bg-danger text-white" : "bg-white/10",
            )}
          >
            <div className={clsx("text-xs", live.late > 0 ? "text-white/80" : "text-white/60")}>
              Fuera de meta
            </div>
            <div className="mt-1 text-3xl font-bold tabular-nums">{live.late}</div>
          </div>
          <div className="rounded-2xl bg-white/10 px-4 py-3">
            <div className="text-xs text-white/60">Espera más larga</div>
            <div className="mt-1 text-3xl font-bold tabular-nums">
              {live.oldest_registered_at ? formatElapsed(live.oldest_registered_at, now) : "—"}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-3 flex gap-3 overflow-x-auto pb-1 [scrollbar-width:none]">
        {live.areas.map((a) => {
          const active = areaId === a.area.id;
          return (
            <button
              key={a.area.id}
              type="button"
              aria-pressed={active}
              onClick={() => onArea(active ? null : a.area.id)}
              className={clsx(
                "w-56 shrink-0 rounded-3xl p-4 text-left shadow-card transition active:scale-[0.98]",
                active ? "bg-ink text-white" : "bg-surface hover:bg-surface-2",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-semibold">{a.area.name}</span>
                {a.late > 0 && (
                  <span
                    title="Fuera de meta"
                    className="min-w-5 shrink-0 rounded-full bg-danger px-1.5 text-center text-[11px] leading-5 font-semibold text-white tabular-nums"
                  >
                    {a.late}
                  </span>
                )}
              </div>
              <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
                {(
                  [
                    ["Por atender", a.registered],
                    ["Atención", a.in_progress],
                    ["Espera", a.waiting],
                  ] as const
                ).map(([label, value]) => (
                  <div key={label}>
                    <dd className="text-xl leading-none font-bold tabular-nums">{value}</dd>
                    <dt
                      className={clsx(
                        "mt-1 text-[10px] leading-tight",
                        active ? "text-white/60" : "text-ink-3",
                      )}
                    >
                      {label}
                    </dt>
                  </div>
                ))}
              </dl>
            </button>
          );
        })}
      </div>
    </section>
  );
}
