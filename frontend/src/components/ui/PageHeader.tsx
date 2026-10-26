import type { ReactNode } from "react";

/** Banner de cabecera: tarjeta blanca con título grande y una forma decorativa en grises. */
export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: ReactNode;
}) {
  return (
    <header className="relative mb-6 overflow-hidden rounded-3xl bg-surface px-6 py-7 shadow-card sm:px-8">
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-16 size-72 rounded-full bg-[radial-gradient(circle_at_30%_30%,#ffffff,#d4d4d8_45%,#71717a_75%,#18181b)] opacity-25 blur-[1px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -right-6 -bottom-20 size-44 rounded-full border-[18px] border-surface-3"
      />
      <div className="relative flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">{title}</h1>
          {subtitle && <p className="mt-1.5 max-w-xl text-sm text-ink-3">{subtitle}</p>}
        </div>
        {children}
      </div>
    </header>
  );
}
