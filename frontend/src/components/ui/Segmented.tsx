import clsx from "clsx";

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
      className="flex gap-0.5 overflow-x-auto rounded-xl bg-surface-3 p-1 [scrollbar-width:none]"
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
              "flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1 text-[13px] font-medium transition",
              active
                ? "bg-surface text-ink shadow-card ring-1 ring-black/5"
                : "text-ink-3 hover:text-ink",
            )}
          >
            {option.label}
            {option.count !== undefined && option.count > 0 && (
              <span
                className={clsx(
                  "min-w-4 rounded-full px-1 text-center text-[10px] leading-4 font-semibold tabular-nums",
                  active ? "bg-ink text-white" : "bg-line-strong text-ink-2",
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
