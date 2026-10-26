import clsx from "clsx";

/** Filtros en píldora: la opción activa va en negro, como en el resto de la consola. */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string; count?: number }[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className="flex gap-1 overflow-x-auto rounded-full bg-surface p-1 shadow-xs ring-1 ring-line [scrollbar-width:none]"
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onChange(option.value)}
            className={clsx(
              "flex h-9 shrink-0 items-center gap-1.5 rounded-full px-4 text-[13px] font-medium transition",
              active
                ? "bg-ink text-white shadow-card"
                : "text-ink-3 hover:bg-surface-3 hover:text-ink",
            )}
          >
            {option.label}
            {option.count !== undefined && option.count > 0 && (
              <span
                className={clsx(
                  "min-w-5 rounded-full px-1.5 text-center text-[11px] leading-5 font-semibold tabular-nums",
                  active ? "bg-white text-ink" : "bg-surface-3 text-ink-2",
                )}
              >
                {option.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
