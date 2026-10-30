import { useCaseMetrics } from "@/api/hooks";
import { ReasonBars } from "./charts";
import { fraction, minutes, percent } from "./format";
import { Card, StatTile } from "./parts";
import { CaseAgentTable, CaseAreaTable } from "./tables";

type Query = { from: string; to: string; area_id?: number };

export function CasePanels({ query }: { query: Query }) {
  const m = useCaseMetrics(query);
  const o = m.overview.data;

  return (
    <>
      {m.overview.error && <p className="mb-4 text-sm text-danger">{m.overview.error.message}</p>}

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          label="Tiempo hasta atender"
          value={minutes(o?.time_to_attention.median)}
          detail={o ? `Mediana · p90 ${minutes(o.time_to_attention.p90)}` : undefined}
          hint="Desde que el caso entra a un área hasta que alguien inicia la atención"
        />
        <StatTile
          label="Meta cumplida"
          value={percent(o?.goal.value)}
          detail={o ? `${fraction(o.goal)} · meta ${o.goal_minutes} min` : undefined}
        />
        <StatTile
          label="Tiempo en atención"
          value={minutes(o?.attention_time.median)}
          detail={o ? `Mediana · p90 ${minutes(o.attention_time.p90)}` : undefined}
          hint="Tiempo en la etapa En atención, por cada paso por un área"
        />
        <StatTile
          label="Resolución"
          value={minutes(o?.resolution_time.median)}
          detail={o ? `Mediana · ${percent(o.resolution_rate.value)} resueltos` : undefined}
          hint="Desde que se crea hasta que se resuelve, sin contar las esperas"
        />
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          label="Casos creados"
          value={o ? String(o.created) : "—"}
          detail={o ? `${o.urgent} urgentes` : undefined}
        />
        <StatTile label="Casos cerrados" value={o ? String(o.closed) : "—"} />
        <StatTile
          label="En espera"
          value={minutes(o?.waiting_time.median)}
          detail={o ? `Mediana · p90 ${minutes(o.waiting_time.p90)}` : undefined}
        />
        <StatTile
          label="Transferidos"
          value={percent(o?.transfer_rate.value)}
          detail={
            o
              ? `${fraction(o.transfer_rate)} · reabiertos ${percent(o.reopen_rate.value)}`
              : undefined
          }
        />
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <Card title="Motivos de cierre" subtitle="Casos cerrados en el período">
          <ReasonBars rows={m.reasons.data ?? []} />
        </Card>
        <Card title="Por área" subtitle="Cada área responde por su propio tramo">
          <CaseAreaTable rows={m.byArea.data ?? []} />
        </Card>
      </div>

      <Card title="Por persona" subtitle="Según lo registrado con su cuenta" className="mb-3">
        <CaseAgentTable rows={m.byAgent.data ?? []} />
      </Card>
    </>
  );
}
