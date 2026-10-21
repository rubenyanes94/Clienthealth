import { ArrowLeft, MessagesSquare } from "lucide-react";
import { Link, useParams } from "react-router";
import { useCatalog, useConversation } from "@/api/hooks";
import type { ConversationEvent } from "@/api/types";
import { displayPhone, EVENT_LABEL, formatDateTime } from "@/lib/format";
import { StatusPill, UrgentPill } from "../inbox/bits";
import { contactName } from "../inbox/permissions";

function useEventDetail() {
  const catalog = useCatalog();
  const areaName = (id: unknown) =>
    catalog.data?.areas.find((a) => a.id === id)?.name ?? (id ? `Área ${id}` : "—");
  const reasonName = (id: unknown) => catalog.data?.reasons.find((r) => r.id === id)?.name;

  return (event: ConversationEvent): string | null => {
    const d = event.data as Record<string, unknown>;
    switch (event.type) {
      case "transferred":
        return `${areaName(d.from_area_id)} → ${areaName(d.to_area_id)}`;
      case "bot_escalated":
        return areaName(d.area_id);
      case "closed":
        return d.by === "bot" ? "Por el bot" : (reasonName(d.reason_id) ?? null);
      case "reopened":
      case "pending_resumed":
        return d.by === "contact" ? "Por el paciente" : null;
      case "agent_message":
        return d.status === "failed" ? "No se pudo entregar" : null;
      default:
        return null;
    }
  };
}

export function CaseDetailPage() {
  const id = Number(useParams().id);
  const conversation = useConversation(Number.isFinite(id) ? id : null);
  const detailOf = useEventDetail();
  const c = conversation.data;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-6">
        <Link
          to="/casos"
          className="mb-4 inline-flex items-center gap-1 text-sm text-ink-2 hover:text-ink"
        >
          <ArrowLeft className="size-4" aria-hidden /> Casos
        </Link>
        {conversation.error && <p className="text-sm text-danger">{conversation.error.message}</p>}
        {c && (
          <>
            <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="text-lg font-semibold">
                  Caso #{c.id} · {contactName(c)}
                </h1>
                <p className="text-sm text-ink-3">{displayPhone(c.contact.wa_id)}</p>
              </div>
              <div className="flex items-center gap-2">
                {c.is_urgent && <UrgentPill />}
                <StatusPill status={c.status} />
                <Link
                  to={`/conversaciones/${c.id}`}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 text-sm font-medium hover:bg-surface-2"
                >
                  <MessagesSquare className="size-4" aria-hidden /> Ver chat
                </Link>
              </div>
            </div>

            <dl className="mb-8 grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line sm:grid-cols-4">
              {[
                ["Área", c.area?.name ?? "—"],
                ["Agente", c.assigned_agent?.name ?? "—"],
                ["Motivo", c.contact_reason?.name ?? "—"],
                ["Prioridad", c.priority === "high" ? "Alta" : "Normal"],
                ["Abierto", formatDateTime(c.opened_at)],
                ["Cerrado", c.closed_at ? formatDateTime(c.closed_at) : "—"],
                ["Mensajes", String(c.messages.filter((m) => !m.is_internal_note).length)],
                ["Notas internas", String(c.messages.filter((m) => m.is_internal_note).length)],
              ].map(([label, value]) => (
                <div key={label} className="bg-surface px-4 py-3">
                  <dt className="text-xs text-ink-3">{label}</dt>
                  <dd className="mt-0.5 text-sm font-medium">{value}</dd>
                </div>
              ))}
            </dl>

            <h2 className="mb-3 text-sm font-semibold">Registro de eventos</h2>
            <ol className="relative ml-2 border-l border-line">
              {c.events.map((e) => {
                const detail = detailOf(e);
                const tone =
                  e.type === "urgency_detected" || e.type === "abandoned"
                    ? "bg-danger"
                    : e.type === "closed"
                      ? "bg-ok"
                      : "bg-brand";
                return (
                  <li key={e.id} className="mb-4 ml-5">
                    <span
                      className={`absolute -left-[5px] mt-1.5 size-2.5 rounded-full ${tone}`}
                      aria-hidden
                    />
                    <div className="text-sm font-medium">
                      {EVENT_LABEL[e.type]}
                      {detail && <span className="font-normal text-ink-2"> · {detail}</span>}
                    </div>
                    <div className="text-xs text-ink-3">
                      {formatDateTime(e.created_at)}
                      {e.agent && ` · ${e.agent.name}`}
                    </div>
                  </li>
                );
              })}
            </ol>
          </>
        )}
      </div>
    </div>
  );
}
