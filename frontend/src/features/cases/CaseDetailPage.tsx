import clsx from "clsx";
import { ArrowLeft, MessagesSquare } from "lucide-react";
import { Link, useParams } from "react-router";
import { useCatalog, useConversation } from "@/api/hooks";
import type { ConversationEvent } from "@/api/types";
import { Avatar } from "@/components/ui/Avatar";
import { displayPhone, EVENT_LABEL, formatDateTime } from "@/lib/format";
import { StatusPill, SurveyPill, UrgentPill } from "../inbox/bits";
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
      case "survey_sent":
        return d.kind === "nps" ? "NPS" : "CSAT";
      case "survey_answered":
        return `${d.kind === "nps" ? "NPS" : "CSAT"} ${String(d.score)}/${d.kind === "nps" ? 10 : 5}`;
      default:
        return null;
    }
  };
}

const DOT: Partial<Record<ConversationEvent["type"], string>> = {
  urgency_detected: "bg-danger",
  abandoned: "bg-danger",
  closed: "bg-ok",
  survey_answered: "bg-ai",
  survey_sent: "bg-ai",
};

export function CaseDetailPage() {
  const id = Number(useParams().id);
  const conversation = useConversation(Number.isFinite(id) ? id : null);
  const detailOf = useEventDetail();
  const c = conversation.data;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-8">
        <Link
          to="/casos"
          className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-ink-3 transition hover:text-ink"
        >
          <ArrowLeft className="size-4" aria-hidden /> Casos
        </Link>
        {conversation.error && <p className="text-sm text-danger">{conversation.error.message}</p>}
        {c && (
          <>
            <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <Avatar name={c.contact.name} urgent={c.is_urgent} />
                <div>
                  <h1 className="text-2xl font-semibold">{contactName(c)}</h1>
                  <p className="text-sm text-ink-3">
                    Caso #{c.id} · {displayPhone(c.contact.wa_id)}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {c.is_urgent && <UrgentPill />}
                <StatusPill status={c.status} />
                {c.surveys.map((s) => (
                  <SurveyPill key={s.id} survey={s} />
                ))}
                <Link
                  to={`/conversaciones/${c.id}`}
                  className="ml-1 inline-flex h-8 items-center gap-1.5 rounded-lg bg-ink px-3 text-[13px] font-medium text-white shadow-xs transition hover:bg-zinc-800"
                >
                  <MessagesSquare className="size-4" aria-hidden /> Ver chat
                </Link>
              </div>
            </div>

            <dl className="mb-10 grid grid-cols-2 overflow-hidden rounded-2xl bg-surface shadow-card ring-1 ring-line sm:grid-cols-4">
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
                <div key={label} className="border-line px-5 py-4 [&:nth-child(-n+4)]:border-b">
                  <dt className="text-[11px] font-semibold tracking-wider text-ink-3 uppercase">
                    {label}
                  </dt>
                  <dd className="mt-1 text-sm font-medium">{value}</dd>
                </div>
              ))}
            </dl>

            <h2 className="mb-4 text-base font-semibold">Registro de eventos</h2>
            <ol className="relative ml-2 border-l border-line">
              {c.events.map((e) => {
                const detail = detailOf(e);
                return (
                  <li key={e.id} className="mb-5 ml-6">
                    <span
                      className={clsx(
                        "absolute -left-[5px] mt-1.5 size-2.5 rounded-full ring-4 ring-white",
                        DOT[e.type] ?? "bg-ink",
                      )}
                      aria-hidden
                    />
                    <div className="text-sm font-medium">
                      {EVENT_LABEL[e.type]}
                      {detail && <span className="font-normal text-ink-3"> · {detail}</span>}
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
