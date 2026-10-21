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
      className="flex gap-1 overflow-x-auto rounded-lg bg-surface-2 p-1"
    >
      {options.map((option) => (
        <button
          key={option.value}
          role="tab"
          type="button"
          aria-selected={option.value === value}
          onClick={() => onChange(option.value)}
          className={clsx(
            "flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1 text-sm font-medium transition",
            option.value === value
              ? "bg-surface text-ink shadow-card"
              : "text-ink-3 hover:text-ink",
          )}
        >
          {option.label}
          {option.count !== undefined && option.count > 0 && (
            <span className="rounded-full bg-brand px-1.5 text-[11px] leading-4 text-brand-ink">
              {option.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
