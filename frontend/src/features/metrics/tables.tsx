import type { components } from "@/api/schema";
import { decimal, minutes, percent } from "./format";
import { Empty } from "./parts";

type AreaRow = components["schemas"]["AreaRow"];
type AgentRow = components["schemas"]["AgentRow"];

const th = "px-6 py-3 text-right font-medium first:text-left";
const td = "px-6 py-3.5 text-right tabular-nums first:text-left";

export function AreaTable({ rows }: { rows: AreaRow[] }) {
  if (rows.length === 0) return <Empty />;
  return (
    <div className="-mx-6 overflow-x-auto">
      <table className="w-full min-w-[40rem] text-sm">
        <thead className="text-xs text-ink-3">
          <tr className="border-b border-line">
            <th className={th}>Área</th>
            <th className={th}>Casos</th>
            <th className={th}>1ª resp. (mediana)</th>
            <th className={th}>SLA</th>
            <th className={th}>Resolución</th>
            <th className={th}>Transferidos</th>
            <th className={th}>Abandono</th>
            <th className={th}>CSAT</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((r) => (
            <tr key={r.area_id ?? "none"}>
              <td className={`${td} font-medium`}>{r.name}</td>
              <td className={td}>{r.episodes}</td>
              <td className={td}>{minutes(r.first_response.median)}</td>
              <td className={td}>{percent(r.sla.value)}</td>
              <td className={td}>{minutes(r.resolution_time.median)}</td>
              <td className={td}>{percent(r.transfer_rate.value)}</td>
              <td className={td}>{percent(r.abandon_rate.value)}</td>
              <td className={td}>{decimal(r.csat.avg, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AgentTable({ rows }: { rows: AgentRow[] }) {
  if (rows.length === 0) return <Empty />;
  return (
    <div className="-mx-6 overflow-x-auto">
      <table className="w-full min-w-[40rem] text-sm">
        <thead className="text-xs text-ink-3">
          <tr className="border-b border-line">
            <th className={th}>Agente</th>
            <th className={th}>Aceptados</th>
            <th className={th}>1ª resp. (mediana)</th>
            <th className={th}>Cerrados</th>
            <th className={th}>Resolución</th>
            <th className={th}>FCR</th>
            <th className={th}>CSAT</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((r) => (
            <tr key={r.agent_id}>
              <td className={`${td} font-medium`}>{r.name}</td>
              <td className={td}>{r.accepted}</td>
              <td className={td}>{minutes(r.first_response.median)}</td>
              <td className={td}>{r.closed}</td>
              <td className={td}>{minutes(r.resolution_time.median)}</td>
              <td className={td}>{percent(r.fcr.value)}</td>
              <td className={td}>
                {decimal(r.csat.avg, 2)}
                {r.csat.responses > 0 && (
                  <span className="ml-1 text-ink-3">({r.csat.responses})</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
