import clsx from "clsx";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "ai";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-ink text-white shadow-card hover:bg-zinc-800",
  secondary: "bg-surface text-ink ring-1 ring-inset ring-line-strong shadow-xs hover:bg-surface-2",
  ghost: "text-ink-2 hover:bg-surface-3 hover:text-ink",
  danger: "bg-danger text-white shadow-xs hover:bg-red-700",
  ai: "bg-ai-soft text-ai ring-1 ring-inset ring-ai/15 hover:bg-violet-100",
};

/** Botón en píldora. "md" mide 44 px de alto: cómodo con el dedo en la tableta. */
export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" | "lg" }) {
  return (
    <button
      type="button"
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-full font-medium whitespace-nowrap",
        "transition duration-150 active:scale-[0.97]",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
        "disabled:pointer-events-none disabled:opacity-40",
        size === "sm" && "h-9 px-4 text-[13px]",
        size === "md" && "h-11 px-5 text-sm",
        size === "lg" && "h-13 px-6 text-[15px]",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}
