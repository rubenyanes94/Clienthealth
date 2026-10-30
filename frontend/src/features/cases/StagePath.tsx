import clsx from "clsx";
import { Check } from "lucide-react";
import { useEffect, useRef } from "react";
import type { CaseEvent, CaseStage } from "@/api/types";
import { pathStates, STAGE_LABEL, STAGES, type StepState } from "./stages";

const NOTCH = "0.875rem";
const FIRST = `polygon(0 0, calc(100% - ${NOTCH}) 0, 100% 50%, calc(100% - ${NOTCH}) 100%, 0 100%)`;
const MIDDLE = `polygon(0 0, calc(100% - ${NOTCH}) 0, 100% 50%, calc(100% - ${NOTCH}) 100%, 0 100%, ${NOTCH} 50%)`;
const LAST = `polygon(0 0, 100% 0, 100% 100%, 0 100%, ${NOTCH} 50%)`;

const STYLES: Record<StepState, string> = {
  done: "bg-zinc-300 text-ink",
  current: "bg-ink font-semibold text-white",
  skipped: "bg-surface-3 text-ink-3",
  todo: "bg-surface-3 text-ink-2",
};

/** Barra de etapas. Solo informa: los cambios se hacen con los botones de al lado. */
export function StagePath({ stage, events }: { stage: CaseStage; events: CaseEvent[] }) {
  const states = pathStates(stage, events);
  const scroller = useRef<HTMLDivElement>(null);

  // En el teléfono la barra no cabe completa: se deja a la vista la etapa actual.
  useEffect(() => {
    const box = scroller.current;
    const current = box?.querySelector<HTMLElement>('[aria-current="step"]');
    if (box && current) box.scrollLeft = current.offsetLeft - box.offsetLeft;
  }, [stage]);

  return (
    <div ref={scroller} className="overflow-x-auto [scrollbar-width:none]">
      <ol className="flex min-w-[38rem]" aria-label="Etapas del caso">
        {STAGES.map((s, i) => (
          <li
            key={s}
            aria-current={states[s] === "current" ? "step" : undefined}
            style={{
              clipPath: i === 0 ? FIRST : i === STAGES.length - 1 ? LAST : MIDDLE,
              marginLeft: i === 0 ? 0 : "-0.5rem",
            }}
            className={clsx(
              "flex h-12 flex-1 items-center justify-center gap-1.5 px-5 text-sm",
              STYLES[states[s]],
            )}
          >
            {states[s] === "done" && <Check className="size-4 shrink-0" aria-hidden />}
            <span className="truncate">{STAGE_LABEL[s]}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
