import type { ConversationDetail, ConversationSummary } from "@/api/types";

const DAY_MS = 24 * 3600_000;

export function permissionsFor(
  conversation: ConversationDetail,
  me: { id: number; role: string } | null | undefined,
) {
  const isSupervisor = me?.role !== "agent";
  const isMine = conversation.assigned_agent?.id === me?.id;
  const canAct = isSupervisor || isMine;
  const active = conversation.status === "open" || conversation.status === "pending";
  const windowOpen =
    !!conversation.last_inbound_at &&
    Date.now() - new Date(conversation.last_inbound_at).getTime() < DAY_MS;

  let blockedReason: string | null = null;
  if (conversation.status === "queued") blockedReason = "Acepte el caso para responder.";
  else if (conversation.status === "bot")
    blockedReason = "El bot está atendiendo esta conversación.";
  else if (conversation.status === "closed") blockedReason = "El caso está cerrado.";
  else if (!canAct) blockedReason = "Este caso está asignado a otro agente.";
  else if (!windowOpen)
    blockedReason = "Pasaron más de 24 h del último mensaje del paciente: solo plantillas.";

  return {
    canAct,
    canReply: active && canAct && windowOpen,
    canNote: conversation.status !== "bot" || isSupervisor,
    blockedReason,
  };
}

export function contactName(conversation: Pick<ConversationSummary, "contact">): string {
  return conversation.contact.name || "Sin nombre";
}
