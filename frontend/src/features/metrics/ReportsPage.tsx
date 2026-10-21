import { Download } from "lucide-react";
import { useMetrics } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { download, toCsv } from "./csv";
import { Filters } from "./Filters";
import { minutes, percent } from "./format";
import { Card, Empty } from "./parts";
import { SupervisorOnly } from "./PanelsPage";
import { AgentTable, AreaTable } from "./tables";
import { usePeriod } from "./usePeriod";

const r = (v: number | null | undefined) => (v === null || v === undefined ? null : v);

export function ReportsPage() {
  const period = usePeriod();
  const m = useMetrics(period.query);
  const suffix = `${period.query.from}_${period.query.to}`;

  const exportButton = (onClick: () => void, disabled: boolean) => (
    <Button size="sm" onClick={onClick} disabled={disabled}>
      <Download className="size-3.5" aria-hidden /> CSV
    </Button>
  );

  return (
    <SupervisorOnly>
      <div className="h-full overflow-y-auto">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold">Informes</h1>
              <p className="mt-1 text-sm text-ink-3">
                Tablas detalladas del período, descargables en CSV (se abren en Excel).
              </p>
            </div>
            <Filters period={period} />
          </div>

          <div className="space-y-6">
            <Card
              title="Por área"
              action={exportButton(
                () =>
                  download(
                    `por-area_${suffix}.csv`,
                    toCsv(
                      [
                        "Área",
                        "Casos",
                        "1ª respuesta mediana (min)",
                        "SLA",
                        "Resolución mediana (min)",
                        "Transferidos",
                        "Abandono",
                        "CSAT promedio",
                        "Respuestas CSAT",
                      ],
                      (m.byArea.data ?? []).map((a) => [
                        a.name,
                        a.episodes,
                        r(a.first_response.median),
                        r(a.sla.value),
                        r(a.resolution_time.median),
                        r(a.transfer_rate.value),
                        r(a.abandon_rate.value),
                        r(a.csat.avg),
                        a.csat.responses,
                      ]),
                    ),
                  ),
                !m.byArea.data?.length,
              )}
            >
              <AreaTable rows={m.byArea.data ?? []} />
            </Card>

            <Card
              title="Por agente"
              action={exportButton(
                () =>
                  download(
                    `por-agente_${suffix}.csv`,
                    toCsv(
                      [
                        "Agente",
                        "Aceptados",
                        "1ª respuesta mediana (min)",
                        "Cerrados",
                        "Resolución mediana (min)",
                        "FCR",
                        "CSAT promedio",
                        "Respuestas CSAT",
                      ],
                      (m.byAgent.data ?? []).map((a) => [
                        a.name,
                        a.accepted,
                        r(a.first_response.median),
                        a.closed,
                        r(a.resolution_time.median),
                        r(a.fcr.value),
                        r(a.csat.avg),
                        a.csat.responses,
                      ]),
                    ),
                  ),
                !m.byAgent.data?.length,
              )}
            >
              <AgentTable rows={m.byAgent.data ?? []} />
            </Card>

            <div className="grid gap-6 lg:grid-cols-2">
              <Card
                title="Por hora"
                subtitle="Hora de Caracas"
                action={exportButton(
                  () =>
                    download(
                      `por-hora_${suffix}.csv`,
                      toCsv(
                        [
                          "Hora",
                          "Mensajes entrantes",
                          "Casos",
                          "1ª respuesta mediana (min)",
                          "SLA",
                        ],
                        (m.byHour.data ?? []).map((h) => [
                          `${h.hour}:00`,
                          h.inbound_messages,
                          h.episodes,
                          r(h.first_response_median),
                          r(h.sla.value),
                        ]),
                      ),
                    ),
                  !m.byHour.data,
                )}
              >
                <div className="-mx-5 max-h-96 overflow-y-auto">
                  <table className="w-full text-[13px]">
                    <thead className="sticky top-0 bg-surface text-[11px] tracking-wider text-ink-3 uppercase">
                      <tr className="border-b border-line">
                        <th className="px-5 py-2 text-left font-semibold">Hora</th>
                        <th className="px-5 py-2 text-right font-semibold">Mensajes</th>
                        <th className="px-5 py-2 text-right font-semibold">Casos</th>
                        <th className="px-5 py-2 text-right font-semibold">1ª resp.</th>
                        <th className="px-5 py-2 text-right font-semibold">SLA</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line tabular-nums">
                      {m.byHour.data
                        ?.filter((h) => h.inbound_messages || h.episodes)
                        .map((h) => (
                          <tr key={h.hour}>
                            <td className="px-5 py-2">{h.hour}:00</td>
                            <td className="px-5 py-2 text-right">{h.inbound_messages}</td>
                            <td className="px-5 py-2 text-right">{h.episodes}</td>
                            <td className="px-5 py-2 text-right">
                              {minutes(h.first_response_median)}
                            </td>
                            <td className="px-5 py-2 text-right">{percent(h.sla.value)}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                  {m.byHour.data &&
                    !m.byHour.data.some((h) => h.inbound_messages || h.episodes) && <Empty />}
                </div>
              </Card>

              <Card
                title="Motivos de contacto"
                action={exportButton(
                  () =>
                    download(
                      `motivos_${suffix}.csv`,
                      toCsv(
                        ["Motivo", "Casos", "Proporción"],
                        (m.reasons.data ?? []).map((x) => [x.name, x.count, r(x.share)]),
                      ),
                    ),
                  !m.reasons.data?.length,
                )}
              >
                {m.reasons.data?.length ? (
                  <ul className="-mx-5 divide-y divide-line text-[13px]">
                    {m.reasons.data.map((x) => (
                      <li key={x.reason_id ?? "none"} className="flex justify-between px-5 py-2">
                        <span>{x.name}</span>
                        <span className="tabular-nums">
                          {x.count} <span className="text-ink-3">· {percent(x.share)}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Empty />
                )}
              </Card>
            </div>
          </div>
        </div>
      </div>
    </SupervisorOnly>
  );
}
