import clsx from "clsx";
import type { ReactNode } from "react";

export type Tone = "neutral" | "brand" | "ok" | "warn" | "danger" | "note" | "ai";

const TONES: Record<Tone, string> = {
  neutral: "bg-surface-3 text-ink-2 ring-zinc-500/10",
  brand: "bg-ink text-white ring-transparent",
  ok: "bg-ok-soft text-ok ring-green-600/15",
  warn: "bg-warn-soft text-warn ring-amber-600/20",
  danger: "bg-danger-soft text-danger ring-red-600/15",
  note: "bg-note-soft text-note ring-yellow-600/20",
  ai: "bg-ai-soft text-ai ring-violet-600/15",
};

export function Pill({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap ring-1 ring-inset",
        TONES[tone],
      )}
    >
      {children}
    </span>
  );
}
