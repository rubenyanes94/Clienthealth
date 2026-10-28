import { Construction } from "lucide-react";

export function Placeholder({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
      <div className="mb-2 flex size-14 items-center justify-center rounded-full bg-ink text-white">
        <Construction className="size-5" aria-hidden />
      </div>
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="max-w-sm text-sm text-ink-3">Disponible en la {phase} del proyecto.</p>
    </div>
  );
}
