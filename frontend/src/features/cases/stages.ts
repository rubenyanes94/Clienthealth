import type { CaseEvent, CaseStage } from "@/api/types";
import type { Tone } from "@/components/ui/Pill";

export const STAGES: CaseStage[] = ["registered", "in_progress", "waiting", "resolved", "closed"];

export const STAGE_LABEL: Record<CaseStage, string> = {
  registered: "Registrado",
  in_progress: "En atención",
  waiting: "En espera",
  resolved: "Resuelto",
  closed: "Cerrado",
};

export const STAGE_TONE: Record<CaseStage, Tone> = {
  registered: "warn",
  in_progress: "brand",
  waiting: "note",
  resolved: "ok",
  closed: "neutral",
};

/** Texto del botón para cada paso permitido: el servidor dice cuáles son (`next_stages`). */
export function stepLabel(from: CaseStage, to: CaseStage): string {
  if (to === "resolved") return "Marcar como resuelto";
  if (to === "closed") return "Cerrar caso";
  if (to === "waiting") return "Poner en espera";
  if (from === "registered") return "Iniciar atención";
  if (from === "waiting") return "Reanudar atención";
  if (from === "resolved") return "Volver a atención";
  return "Reabrir caso";
}

export type StepState = "done" | "current" | "skipped" | "todo";

/** Estado de cada tramo de la barra. "En espera" es opcional: si no se pasó por ahí, no se marca. */
export function pathStates(stage: CaseStage, events: CaseEvent[]): Record<CaseStage, StepState> {
  const current = STAGES.indexOf(stage);
  const waited = events.some((e) => e.type === "stage_changed" && e.data.to === "waiting");
  const state = (s: CaseStage, i: number): StepState => {
    if (i === current) return "current";
    if (i > current) return "todo";
    return s === "waiting" && !waited ? "skipped" : "done";
  };
  return Object.fromEntries(STAGES.map((s, i) => [s, state(s, i)])) as Record<CaseStage, StepState>;
}
