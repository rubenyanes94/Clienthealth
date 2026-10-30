import clsx from "clsx";
import { ChevronRight, Clock, Plus, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useCases, useCasesLive, useCatalog } from "@/api/hooks";
import type { CaseStage, CaseSummary } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pill, type Tone } from "@/components/ui/Pill";
import { Segmented } from "@/components/ui/Segmented";
import { fieldClass } from "@/components/ui/Sheet";
import { formatElapsed } from "@/lib/format";
import { useDebounced } from "@/lib/useDebounced";
import { useNow } from "@/lib/useNow";
import { NewCaseDialog } from "./NewCaseDialog";
import { RoomBoard } from "./RoomBoard";
import { StagePill } from "./StagePill";
import { STAGE_LABEL } from "./stages";

type StageFilter = CaseStage | "open";

const OPTIONS: { value: StageFilter; label: string }[] = [
  { value: "open", label: "Abiertos" },
  { value: "registered", label: STAGE_LABEL.registered },
  { value: "in_progress", label: STAGE_LABEL.in_progress },
  { value: "waiting", label: STAGE_LABEL.waiting },
  { value: "resolved", label: STAGE_LABEL.resolved },
  { value: "closed", label: "Cerrados" },
];

/** Tiempo en la etapa actual. Un caso por atender se compara con la meta de su área. */
function StageTimer({ item }: { item: CaseSummary }) {
  const now = useNow();
  if (item.stage === "closed") return <span className="text-ink-3">—</span>;
  const goal = item.area.sla_first_response_minutes * 60_000;
  const waited = now - new Date(item.stage_changed_at).getTime();
  let tone: Tone = "neutral";
  if (item.stage === "registered") {
    tone = waited >= goal ? "danger" : waited >= goal * 0.75 ? "warn" : "ok";
  }
  return (
    <Pill tone={tone}>
      <Clock className="size-3" aria-hidden />
      <span className="tabular-nums">{formatElapsed(item.stage_changed_at, now)}</span>
    </Pill>
  );
}

export function CasesPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState("");
  const [mine, setMine] = useState(false);
  const [creating, setCreating] = useState(false);
  const debounced = useDebounced(q);
  const catalog = useCatalog();
  const live = useCasesLive();

  const stage = OPTIONS.find((o) => o.value === params.get("etapa"))?.value ?? "open";
  const rawArea = Number(params.get("area"));
  const areaId = Number.isInteger(rawArea) && rawArea > 0 ? rawArea : null;

  const setFilter = (next: { stage?: StageFilter; area?: number | null }) => {
    const nextStage = next.stage ?? stage;
    const nextArea = next.area === undefined ? areaId : next.area;
    const out: Record<string, string> = {};
    if (nextStage !== "open") out.etapa = nextStage;
    if (nextArea !== null) out.area = String(nextArea);
    setParams(out, { replace: true });
  };

  const cases = useCases({ stage, area_id: areaId, mine, q: debounced, cursor: null });

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl px-3 py-3 sm:px-4 md:py-0">
        <PageHeader title="Casos" subtitle="Gestión entre áreas y situación de la sala.">
          <Button size="lg" variant="primary" onClick={() => setCreating(true)}>
            <Plus className="size-5" aria-hidden /> Nuevo caso
          </Button>
        </PageHeader>

        {live.data && (
          <RoomBoard
            live={live.data}
            stage={stage}
            areaId={areaId}
            onStage={(s) => setFilter({ stage: s })}
            onArea={(a) => setFilter({ area: a })}
          />
        )}

        <div className="mb-3 flex flex-wrap items-center gap-3">
          <Segmented
            label="Etapa de los casos"
            options={OPTIONS}
            value={stage}
            onChange={(s) => setFilter({ stage: s })}
          />
          <button
            type="button"
            aria-pressed={mine}
            onClick={() => setMine((v) => !v)}
            className={clsx(
              "h-11 rounded-full px-5 text-[13px] font-medium shadow-xs ring-1 ring-line transition",
              mine ? "bg-ink text-white" : "bg-surface text-ink-2 hover:bg-surface-2",
            )}
          >
            Mis casos
          </button>
          <label className="sr-only" htmlFor="case-area">
            Área
          </label>
          <select
            id="case-area"
            value={areaId ?? ""}
            onChange={(e) => setFilter({ area: e.target.value ? Number(e.target.value) : null })}
            className="h-11 w-52 rounded-full bg-surface px-4 text-sm shadow-xs ring-1 ring-line outline-none ring-inset focus:ring-2 focus:ring-ink"
          >
            <option value="">Todas las áreas</option>
            {catalog.data?.areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
          <div className="relative min-w-56 flex-1">
            <Search
              className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-ink-3"
              aria-hidden
            />
            <label className="sr-only" htmlFor="case-search">
              Buscar caso
            </label>
            <input
              id="case-search"
              type="search"
              autoComplete="off"
              placeholder="Buscar por asunto, paciente, cédula o número…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className={`${fieldClass} h-11 rounded-full bg-surface pl-11 text-sm ring-line`}
            />
          </div>
        </div>

        <div className="mb-3 overflow-x-auto rounded-3xl bg-surface shadow-card">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="text-xs text-ink-3">
              <tr className="border-b border-line">
                <th className="px-4 py-4 font-medium">Caso</th>
                <th className="px-4 py-4 font-medium">Paciente</th>
                <th className="px-4 py-4 font-medium">Área y responsable</th>
                <th className="px-4 py-4 font-medium">Etapa</th>
                <th className="px-4 py-4 font-medium">En etapa</th>
                <th className="w-10" aria-hidden />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {cases.data?.items.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/casos/${c.id}`)}
                  className="group cursor-pointer transition hover:bg-surface-2 active:bg-surface-3"
                >
                  <td className="max-w-72 px-4 py-4">
                    <a
                      href={`/casos/${c.id}`}
                      onClick={(e) => e.preventDefault()}
                      className="block truncate font-semibold hover:underline"
                    >
                      {c.subject}
                    </a>
                    <span className="text-xs text-ink-3 tabular-nums">#{c.id}</span>
                  </td>
                  <td className="px-4 py-4">
                    <div className="font-medium">
                      {c.patient.first_name} {c.patient.last_name}
                    </div>
                    <div className="text-xs text-ink-3 tabular-nums">{c.patient.national_id}</div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="text-ink-2">{c.area.name}</div>
                    <div className="text-xs text-ink-3">
                      {c.assigned_agent?.name ?? "Sin asignar"}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex flex-wrap gap-1">
                      {c.priority === "high" && <Pill tone="danger">Urgente</Pill>}
                      <StagePill stage={c.stage} />
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <StageTimer item={c} />
                  </td>
                  <td className="pr-5">
                    <span className="flex size-8 items-center justify-center rounded-full bg-surface-3 text-ink-3 transition group-hover:bg-ink group-hover:text-white">
                      <ChevronRight className="size-4" aria-hidden />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {cases.isPending && <p className="p-6 text-sm text-ink-3">Cargando…</p>}
          {cases.error && <p className="p-6 text-sm text-danger">{cases.error.message}</p>}
          {cases.data?.items.length === 0 && (
            <p className="p-12 text-center text-sm text-ink-3">No hay casos con estos filtros.</p>
          )}
          {cases.data?.next_cursor && (
            <p className="border-t border-line p-4 text-center text-xs text-ink-3">
              Se muestran los primeros 50. Use la búsqueda o los filtros para acotar.
            </p>
          )}
        </div>
      </div>
      <NewCaseDialog open={creating} onClose={() => setCreating(false)} />
    </div>
  );
}
