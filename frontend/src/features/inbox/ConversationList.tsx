import clsx from "clsx";
import { Inbox } from "lucide-react";
import { Link } from "react-router";
import { useInbox, useLiveMetrics, useMe } from "@/api/hooks";
import type { InboxFilter } from "@/api/types";
import { Segmented } from "@/components/ui/Segmented";
import { displayPhone, formatListTime } from "@/lib/format";
import { StatusPill, UrgentPill, WaitTimer } from "./bits";
import { contactName } from "./permissions";

const SENDER_PREFIX = { agent: "Agente", bot: "Bot", system: "Automático" } as const;

export function ConversationList({
  filter,
  onFilter,
  selectedId,
}: {
  filter: InboxFilter;
  onFilter: (filter: InboxFilter) => void;
  selectedId: number | null;
}) {
  const me = useMe();
  const live = useLiveMetrics();
  const inbox = useInbox(filter);
  const isSupervisor = me.data?.role !== "agent";

  const options: { value: InboxFilter; label: string; count?: number }[] = [
    { value: "open", label: "Abiertas" },
    { value: "queue", label: "Cola", count: live.data?.queued },
    { value: "mine", label: "Mías" },
    { value: "pending", label: "En espera" },
    { value: "closed", label: "Cerradas" },
  ];
  if (isSupervisor) options.push({ value: "bot", label: "Bot", count: live.data?.in_bot });

  return (
    <section aria-label="Bandeja" className="flex h-full min-h-0 flex-col">
      <div className="border-b border-line p-3">
        <Segmented
          label="Filtro de la bandeja"
          options={options}
          value={filter}
          onChange={onFilter}
        />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {inbox.isPending && <p className="p-4 text-sm text-ink-3">Cargando…</p>}
        {inbox.error && <p className="p-4 text-sm text-danger">{inbox.error.message}</p>}
        {inbox.data?.items.length === 0 && (
          <div className="flex flex-col items-center gap-2 p-10 text-center text-sm text-ink-3">
            <Inbox className="size-6" aria-hidden />
            No hay conversaciones aquí.
          </div>
        )}
        <ul>
          {inbox.data?.items.map((c) => (
            <li key={c.id}>
              <Link
                to={`/conversaciones/${c.id}?filtro=${filter}`}
                aria-current={c.id === selectedId ? "true" : undefined}
                className={clsx(
                  "block border-b border-line px-4 py-3 transition hover:bg-surface-2",
                  c.id === selectedId && "bg-brand-soft/60",
                  c.is_urgent && "border-l-4 border-l-danger",
                )}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-sm font-semibold">{contactName(c)}</span>
                  {c.last_message_at && (
                    <time className="shrink-0 text-xs text-ink-3" dateTime={c.last_message_at}>
                      {formatListTime(c.last_message_at)}
                    </time>
                  )}
                </div>
                <div className="truncate text-xs text-ink-3">{displayPhone(c.contact.wa_id)}</div>
                {c.last_message_preview && (
                  <p className="mt-1 line-clamp-1 text-sm text-ink-2">
                    {c.last_message_sender && c.last_message_sender !== "contact" && (
                      <span className="text-ink-3">{SENDER_PREFIX[c.last_message_sender]}: </span>
                    )}
                    {c.last_message_preview}
                  </p>
                )}
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  {c.is_urgent && <UrgentPill />}
                  <StatusPill status={c.status} />
                  {c.area && <span className="text-xs text-ink-3">{c.area.name}</span>}
                  <WaitTimer conversation={c} />
                  {c.assigned_agent && c.status !== "queued" && (
                    <span className="ml-auto text-xs text-ink-3">{c.assigned_agent.name}</span>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
