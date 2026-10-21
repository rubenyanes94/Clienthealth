import { Construction } from "lucide-react";

export function Placeholder({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
      <Construction className="size-8 text-ink-3" aria-hidden />
      <h1 className="text-lg font-semibold">{title}</h1>
      <p className="max-w-sm text-sm text-ink-3">Disponible en la {phase} del proyecto.</p>
    </div>
  );
}
