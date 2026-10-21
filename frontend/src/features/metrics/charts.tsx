import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { components } from "@/api/schema";
import { AXIS_TICK, GRID, SERIES_1 } from "./chartTheme";
import { decimal, minutes, percent } from "./format";
import { ChartTooltip, Empty } from "./parts";

type HourRow = components["schemas"]["HourRow"];
type CsatDay = components["schemas"]["CsatDay"];
type ReasonRow = components["schemas"]["ReasonRow"];

const dayFmt = new Intl.DateTimeFormat("es-VE", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

export function HourBars({ rows }: { rows: HourRow[] }) {
  if (!rows.some((r) => r.inbound_messages > 0)) return <Empty />;
  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          margin={{ top: 4, right: 4, bottom: 0, left: -20 }}
          barCategoryGap={2}
        >
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis
            dataKey="hour"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: GRID }}
            interval={2}
            tickFormatter={(h: number) => `${h}h`}
          />
          <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: "rgb(9 9 11 / 0.04)" }}
            content={({ active, payload }) => {
              const row = payload?.[0]?.payload as HourRow | undefined;
              if (!active || !row) return null;
              return (
                <ChartTooltip
                  title={`${row.hour}:00 – ${row.hour}:59`}
                  rows={[
                    ["Mensajes entrantes", String(row.inbound_messages)],
                    ["Casos que entraron en cola", String(row.episodes)],
                    ["1ª respuesta (mediana)", minutes(row.first_response_median)],
                    ["SLA cumplido", percent(row.sla.value)],
                  ]}
                />
              );
            }}
          />
          <Bar
            dataKey="inbound_messages"
            name="Mensajes entrantes"
            fill={SERIES_1}
            radius={[4, 4, 0, 0]}
            maxBarSize={18}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CsatLine({ rows }: { rows: CsatDay[] }) {
  if (!rows.some((r) => r.responses > 0)) return <Empty>Aún no hay encuestas respondidas.</Empty>;
  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis
            dataKey="day"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: GRID }}
            tickFormatter={(d: string) => dayFmt.format(new Date(`${d}T00:00:00Z`))}
            minTickGap={24}
          />
          <YAxis
            domain={[1, 5]}
            ticks={[1, 2, 3, 4, 5]}
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ stroke: GRID, strokeWidth: 1 }}
            content={({ active, payload }) => {
              const row = payload?.[0]?.payload as CsatDay | undefined;
              if (!active || !row) return null;
              return (
                <ChartTooltip
                  title={dayFmt.format(new Date(`${row.day}T00:00:00Z`))}
                  rows={[
                    ["Promedio", row.avg === null ? "—" : `${decimal(row.avg, 2)} / 5`],
                    ["Satisfechos (4–5)", percent(row.satisfied)],
                    ["Respuestas", String(row.responses)],
                  ]}
                />
              );
            }}
          />
          <Line
            type="monotone"
            dataKey="avg"
            name="CSAT promedio"
            stroke={SERIES_1}
            strokeWidth={2}
            // Puntos siempre visibles: un día con respuestas entre días sin datos no tiene línea.
            dot={{ r: 4, fill: SERIES_1, stroke: "#fff", strokeWidth: 2 }}
            activeDot={{ r: 5, stroke: "#fff", strokeWidth: 2 }}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Barras horizontales en HTML: cada fila es legible sin gráfico y accesible como lista. */
export function ReasonBars({ rows }: { rows: ReasonRow[] }) {
  if (rows.length === 0) return <Empty>Sin casos cerrados en este período.</Empty>;
  const max = Math.max(...rows.map((r) => r.count));
  return (
    <ul className="space-y-3">
      {rows.slice(0, 8).map((r) => (
        <li key={r.reason_id ?? "none"} title={`${r.count} casos · ${percent(r.share)}`}>
          <div className="mb-1 flex justify-between gap-3 text-[13px]">
            <span className="truncate text-ink-2">{r.name}</span>
            <span className="shrink-0 font-medium tabular-nums">
              {r.count} <span className="font-normal text-ink-3">· {percent(r.share)}</span>
            </span>
          </div>
          <div className="h-2 rounded-full bg-surface-3">
            <div
              className="h-2 rounded-full"
              style={{ width: `${(r.count / max) * 100}%`, background: SERIES_1 }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
