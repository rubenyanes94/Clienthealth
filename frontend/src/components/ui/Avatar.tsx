import clsx from "clsx";

function initials(name: string | null | undefined): string {
  const words = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  return (
    (words[0]?.[0] ?? "") + (words.length > 1 ? (words.at(-1)?.[0] ?? "") : "")
  ).toUpperCase();
}

export function Avatar({
  name,
  size = "md",
  urgent = false,
}: {
  name: string | null | undefined;
  size?: "sm" | "md";
  urgent?: boolean;
}) {
  return (
    <span
      aria-hidden
      className={clsx(
        "relative inline-flex shrink-0 items-center justify-center rounded-full bg-surface-3 font-semibold text-ink-2 ring-1 ring-black/5",
        size === "sm" ? "size-8 text-[11px]" : "size-10 text-[13px]",
      )}
    >
      {initials(name)}
      {urgent && (
        <span className="absolute -top-0.5 -right-0.5 size-3 rounded-full bg-danger ring-2 ring-white" />
      )}
    </span>
  );
}
