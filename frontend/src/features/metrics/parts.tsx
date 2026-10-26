import clsx from "clsx";
import type { ReactNode } from "react";

export function Card({
  title,
  subtitle,
  action,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={clsx("rounded-3xl bg-surface p-6 shadow-card", className)}
      aria-label={title}
    >
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-ink-3">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function StatTile({
  label,
  value,
  detail,
  hint,
}: {
  label: string;
  value: string;
  detail?: string;
  hint?: string;
}) {
  return (
    <div className="rounded-3xl bg-surface p-5 shadow-card" title={hint}>
      <div className="text-[13px] font-medium text-ink-3">{label}</div>
      <div className="mt-3 text-4xl leading-none font-bold tracking-tight tabular-nums">
        {value}
      </div>
      {detail && <div className="mt-3 text-xs text-ink-3">{detail}</div>}
    </div>
  );
}

export function ChartTooltip({ title, rows }: { title: string; rows: [string, string][] }) {
  return (
    <div className="rounded-2xl bg-surface px-4 py-3 text-xs shadow-pop">
      <div className="mb-1 font-semibold text-ink">{title}</div>
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between gap-4 text-ink-2">
          <span>{label}</span>
          <span className="font-medium text-ink tabular-nums">{value}</span>
        </div>
      ))}
    </div>
  );
}

export function Empty({ children = "Sin datos en este período." }: { children?: ReactNode }) {
  return <p className="py-10 text-center text-sm text-ink-3">{children}</p>;
}
