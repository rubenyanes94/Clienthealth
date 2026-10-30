import { Download } from "lucide-react";
import { useCaseMetrics } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { download, toCsv } from "./csv";
import { percent } from "./format";
import { Card, Empty } from "./parts";
import { CaseAgentTable, CaseAreaTable } from "./tables";

type Query = { from: string; to: string; area_id?: number };

const r = (v: number | null | undefined) => (v === null || v === undefined ? null : v);

export function CaseReports({ query }: { query: Query }) {
  const m = useCaseMetrics(query);
  const suffix = `${query.from}_${query.to}`;

  const exportButton = (onClick: () => void, disabled: boolean) => (
    <Button size="sm" onClick={onClick} disabled={disabled}>
      <Download className="size-3.5" aria-hidden /> CSV
    </Button>
  );

  return (
    <div className="space-y-4 pb-3">
      <Card
        title="Por área"
        action={exportButton(
          () =>
            download(
              `casos-por-area_${suffix}.csv`,
              toCsv(
                [
                  "Área",
                  "Recibidos",
                  "Cerrados",
                  "Hasta atender mediana (min)",
                  "Meta cumplida",
                  "En atención mediana (min)",
                  "En espera mediana (min)",
                ],
                (m.byArea.data ?? []).map((a) => [
                  a.name,
                  a.received,
                  a.closed,
                  r(a.time_to_attention.median),
                  r(a.goal.value),
                  r(a.attention_time.median),
                  r(a.waiting_time.median),
                ]),
              ),
            ),
          !m.byArea.data?.length,
        )}
      >
        <CaseAreaTable rows={m.byArea.data ?? []} />
      </Card>

      <Card
        title="Por persona"
        action={exportButton(
          () =>
            download(
              `casos-por-persona_${suffix}.csv`,
              toCsv(
                [
                  "Persona",
                  "Atendidos",
                  "Resueltos",
                  "Cerrados",
                  "Transferidos",
                  "En atención mediana (min)",
                ],
                (m.byAgent.data ?? []).map((a) => [
                  a.name,
                  a.attended,
                  a.resolved,
                  a.closed,
                  a.transferred,
                  r(a.attention_time.median),
                ]),
              ),
            ),
          !m.byAgent.data?.length,
        )}
      >
        <CaseAgentTable rows={m.byAgent.data ?? []} />
      </Card>

      <Card
        title="Motivos de cierre"
        action={exportButton(
          () =>
            download(
              `casos-motivos_${suffix}.csv`,
              toCsv(
                ["Motivo", "Casos", "Proporción"],
                (m.reasons.data ?? []).map((x) => [x.name, x.count, r(x.share)]),
              ),
            ),
          !m.reasons.data?.length,
        )}
      >
        {m.reasons.data?.length ? (
          <ul className="-mx-6 divide-y divide-line text-sm">
            {m.reasons.data.map((x) => (
              <li key={x.reason_id ?? "none"} className="flex justify-between px-6 py-2.5">
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
  );
}
