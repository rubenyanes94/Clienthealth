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
  size?: "sm" | "md" | "lg";
  urgent?: boolean;
}) {
  return (
    <span
      aria-hidden
      className={clsx(
        "relative inline-flex shrink-0 items-center justify-center rounded-full bg-surface-3 font-semibold text-ink-2 ring-2 ring-white",
        size === "sm" && "size-9 text-xs",
        size === "md" && "size-11 text-sm",
        size === "lg" && "size-16 text-lg",
      )}
    >
      {initials(name)}
      {urgent && (
        <span className="absolute -top-0.5 -right-0.5 size-3 rounded-full bg-danger ring-2 ring-white" />
      )}
    </span>
  );
}
