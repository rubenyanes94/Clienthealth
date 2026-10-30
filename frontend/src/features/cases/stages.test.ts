import type { CaseEvent } from "@/api/types";
import { pathStates, stepLabel } from "./stages";

const waitedEvent = {
  id: 1,
  type: "stage_changed",
  agent: null,
  area_id: 1,
  data: { from: "in_progress", to: "waiting" },
  created_at: "2026-10-30T12:00:00Z",
} as CaseEvent;

describe("pathStates", () => {
  it("marca lo anterior como hecho y lo siguiente como pendiente", () => {
    expect(pathStates("in_progress", [])).toEqual({
      registered: "done",
      in_progress: "current",
      waiting: "todo",
      resolved: "todo",
      closed: "todo",
    });
  });

  it("no marca «En espera» si el caso nunca estuvo en espera", () => {
    expect(pathStates("resolved", []).waiting).toBe("skipped");
    expect(pathStates("resolved", [waitedEvent]).waiting).toBe("done");
  });
});

describe("stepLabel", () => {
  it("nombra cada paso según de dónde viene", () => {
    expect(stepLabel("registered", "in_progress")).toBe("Iniciar atención");
    expect(stepLabel("waiting", "in_progress")).toBe("Reanudar atención");
    expect(stepLabel("resolved", "in_progress")).toBe("Volver a atención");
    expect(stepLabel("closed", "in_progress")).toBe("Reabrir caso");
  });
});
