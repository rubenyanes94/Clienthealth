import type { ConversationDetail } from "@/api/types";
import { permissionsFor } from "./permissions";

function conversation(overrides: Partial<ConversationDetail> = {}): ConversationDetail {
  return {
    id: 1,
    contact: { id: 1, wa_id: "584141234567", name: "María" },
    area: { id: 2, name: "Laboratorio", sla_first_response_minutes: 15 },
    assigned_agent: { id: 7, name: "Ana" },
    status: "open",
    priority: "normal",
    is_urgent: false,
    opened_at: new Date().toISOString(),
    queued_at: null,
    pending_since: null,
    closed_at: null,
    last_message_at: new Date().toISOString(),
    last_inbound_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    contact_reason: null,
    messages: [],
    events: [],
    ...overrides,
  };
}

describe("permissionsFor", () => {
  it("permite responder al agente asignado dentro de la ventana", () => {
    const p = permissionsFor(conversation(), { id: 7, role: "agent" });
    expect(p.canReply).toBe(true);
  });

  it("bloquea a otro agente", () => {
    const p = permissionsFor(conversation(), { id: 8, role: "agent" });
    expect(p.canReply).toBe(false);
    expect(p.blockedReason).toMatch(/otro agente/);
  });

  it("bloquea fuera de la ventana de 24 h", () => {
    const old = new Date(Date.now() - 25 * 3600_000).toISOString();
    const p = permissionsFor(conversation({ last_inbound_at: old }), { id: 7, role: "agent" });
    expect(p.canReply).toBe(false);
    expect(p.blockedReason).toMatch(/24 h/);
  });

  it("pide aceptar los casos en cola", () => {
    const p = permissionsFor(conversation({ status: "queued", assigned_agent: null }), {
      id: 7,
      role: "agent",
    });
    expect(p.blockedReason).toMatch(/Acepte/);
  });
});
