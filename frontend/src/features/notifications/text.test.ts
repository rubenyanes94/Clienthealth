import type { AppNotification } from "@/api/types";
import { notificationText } from "./text";

const base = {
  id: 1,
  created_at: "2026-10-30T15:00:00Z",
  read_at: null,
  actor: { id: 2, name: "Ana" },
  case: { id: 14, subject: "Seguimiento", patient_name: "María Pérez" },
} as const;

describe("notificationText", () => {
  it("describe una tarea asignada según su tipo", () => {
    const n = { ...base, type: "task_assigned", task_type: "call" } as AppNotification;
    expect(notificationText(n)).toEqual({
      title: "Nueva tarea: Llamar",
      body: "Ana le asignó llamar a María Pérez · Caso #14",
    });
    expect(notificationText({ ...n, task_type: "email" }).body).toContain("enviar un correo a");
  });

  it("describe un caso asignado", () => {
    const n = { ...base, type: "case_assigned", task_type: null } as AppNotification;
    expect(notificationText(n)).toEqual({
      title: "Caso asignado",
      body: "Ana le asignó el caso #14 «Seguimiento» de María Pérez",
    });
  });

  it("no falla si se borró el autor", () => {
    const n = { ...base, actor: null, type: "case_assigned", task_type: null } as AppNotification;
    expect(notificationText(n).body.startsWith("Alguien")).toBe(true);
  });
});
