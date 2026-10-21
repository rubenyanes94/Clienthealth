import { Construction } from "lucide-react";

export function Placeholder({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
      <div className="mb-2 flex size-12 items-center justify-center rounded-2xl bg-surface-3">
        <Construction className="size-5 text-ink-2" aria-hidden />
      </div>
      <h1 className="text-lg font-semibold">{title}</h1>
      <p className="max-w-sm text-sm text-ink-3">Disponible en la {phase} del proyecto.</p>
    </div>
  );
}
