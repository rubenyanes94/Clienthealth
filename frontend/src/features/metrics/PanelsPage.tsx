import { Lock } from "lucide-react";
import type { ReactNode } from "react";
import { useLiveMetrics, useMe, useMetrics } from "@/api/hooks";
import { formatElapsed } from "@/lib/format";
import { useNow } from "@/lib/useNow";
import { CsatLine, HourBars, ReasonBars } from "./charts";
import { Filters } from "./Filters";
import { decimal, fraction, minutes, percent } from "./format";
import { AgentTable, AreaTable } from "./tables";
import { Card, StatTile } from "./parts";
import { usePeriod } from "./usePeriod";

export function SupervisorOnly({ children }: { children: ReactNode }) {
  const me = useMe();
  if (me.data?.role === "agent") {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-surface-3">
          <Lock className="size-5 text-ink-2" aria-hidden />
        </div>
        <p className="text-sm text-ink-3">Los indicadores están disponibles para supervisores.</p>
      </div>
    );
  }
  return children;
}

function LiveStrip() {
  const live = useLiveMetrics();
  const now = useNow();
  if (!live.data) return null;
  const items: [string, string][] = [
    ["En cola", String(live.data.queued)],
    ["Urgentes en cola", String(live.data.urgent_queued)],
    [
      "Espera más larga",
      live.data.oldest_queued_at ? formatElapsed(live.data.oldest_queued_at, now) : "—",
    ],
    ["En el bot", String(live.data.in_bot)],
    ["Abiertas", String(live.data.open)],
    ["Agentes conectados", String(live.data.agents_online)],
  ];
  return (
    <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-2xl bg-ink px-5 py-3 text-white">
      <span className="flex items-center gap-2 text-xs font-semibold tracking-wider uppercase">
        <span className="size-2 animate-pulse rounded-full bg-green-400" aria-hidden /> Ahora
      </span>
      {items.map(([label, value]) => (
        <span key={label} className="text-sm">
          <span className="text-white/60">{label} </span>
          <span className="font-semibold tabular-nums">{value}</span>
        </span>
      ))}
    </div>
  );
}

export function PanelsPage() {
  const period = usePeriod();
  const m = useMetrics(period.query);
  const o = m.overview.data;

  return (
    <SupervisorOnly>
      <div className="h-full overflow-y-auto">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold">Paneles</h1>
              <p className="mt-1 text-sm text-ink-3">
                Tiempos en minutos hábiles. Definiciones en el diccionario de indicadores.
              </p>
            </div>
            <Filters period={period} />
          </div>

          <LiveStrip />

          {m.overview.error && (
            <p className="mb-4 text-sm text-danger">{m.overview.error.message}</p>
          )}

          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatTile
              label="1ª respuesta"
              value={minutes(o?.first_response.median)}
              detail={o ? `Mediana · p90 ${minutes(o.first_response.p90)}` : undefined}
            />
            <StatTile
              label="SLA cumplido"
              value={percent(o?.sla.value)}
              detail={o ? fraction(o.sla) : undefined}
            />
            <StatTile
              label="CSAT"
              value={o?.csat.avg ? `${decimal(o.csat.avg, 2)} / 5` : "—"}
              detail={
                o
                  ? `${percent(o.csat.satisfied.value)} satisfechos · ${o.csat.responses} resp.`
                  : undefined
              }
            />
            <StatTile
              label="NPS"
              value={o?.nps.score === null || !o ? "—" : decimal(o.nps.score, 0)}
              detail={o ? `${o.nps.responses} respuestas` : undefined}
            />
            <StatTile
              label="Resolución"
              value={minutes(o?.resolution_time.median)}
              detail={o ? `Mediana · ${percent(o.resolution_rate.value)} resueltos` : undefined}
            />
            <StatTile
              label="Resueltos al 1er contacto"
              value={percent(o?.fcr.value)}
              detail={o ? fraction(o.fcr) : undefined}
              hint="Se evalúa cuando vence la ventana de reapertura"
            />
            <StatTile
              label="Abandono"
              value={percent(o?.abandon_rate.value)}
              detail={o ? fraction(o.abandon_rate) : undefined}
            />
            <StatTile
              label="Resueltas por el bot"
              value={percent(o?.bot_containment.value)}
              detail={o ? fraction(o.bot_containment) : undefined}
            />
          </div>

          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatTile label="Conversaciones" value={o ? String(o.conversations) : "—"} />
            <StatTile label="Casos atendidos" value={o ? String(o.episodes) : "—"} />
            <StatTile label="Urgencias" value={o ? String(o.urgent) : "—"} />
            <StatTile
              label="Transferencias"
              value={percent(o?.transfer_rate.value)}
              detail={o ? `Reaperturas ${percent(o.reopen_rate.value)}` : undefined}
            />
          </div>

          <div className="mb-6 grid gap-6 lg:grid-cols-2">
            <Card title="Mensajes entrantes por hora" subtitle="Hora de Caracas">
              <HourBars rows={m.byHour.data ?? []} />
            </Card>
            <Card title="CSAT promedio por día" subtitle="Escala de 1 a 5">
              <CsatLine rows={m.csatDaily.data ?? []} />
            </Card>
          </div>

          <div className="mb-6 grid gap-6 lg:grid-cols-[1fr_2fr]">
            <Card title="Motivos de contacto" subtitle="Casos cerrados en el período">
              <ReasonBars rows={m.reasons.data ?? []} />
            </Card>
            <Card title="Por área">
              <AreaTable rows={m.byArea.data ?? []} />
            </Card>
          </div>

          <Card title="Por agente">
            <AgentTable rows={m.byAgent.data ?? []} />
          </Card>
        </div>
      </div>
    </SupervisorOnly>
  );
}
