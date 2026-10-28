import clsx from "clsx";
import { Inbox } from "lucide-react";
import { Link } from "react-router";
import { useInbox, useLiveMetrics, useMe } from "@/api/hooks";
import type { InboxFilter } from "@/api/types";
import { Avatar } from "@/components/ui/Avatar";
import { Segmented } from "@/components/ui/Segmented";
import { formatListTime } from "@/lib/format";
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
      <div className="px-4 pb-4">
        <Segmented
          label="Filtro de la bandeja"
          options={options}
          value={filter}
          onChange={onFilter}
        />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
        {inbox.isPending && <p className="p-4 text-sm text-ink-3">Cargando…</p>}
        {inbox.error && <p className="p-4 text-sm text-danger">{inbox.error.message}</p>}
        {inbox.data?.items.length === 0 && (
          <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
            <div className="flex size-14 items-center justify-center rounded-full bg-surface-3">
              <Inbox className="size-5 text-ink-2" aria-hidden />
            </div>
            <p className="text-sm text-ink-3">No hay conversaciones aquí.</p>
          </div>
        )}
        <ul className="space-y-1">
          {inbox.data?.items.map((c) => {
            const selected = c.id === selectedId;
            return (
              <li key={c.id}>
                <Link
                  to={`/conversaciones/${c.id}?filtro=${filter}`}
                  aria-current={selected ? "true" : undefined}
                  className={clsx(
                    "relative flex gap-3 rounded-2xl px-3 py-4 transition active:scale-[0.99]",
                    selected ? "bg-surface-3 ring-1 ring-line-strong" : "hover:bg-surface-2",
                  )}
                >
                  <Avatar name={c.contact.name} urgent={c.is_urgent} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="truncate text-[15px] font-semibold">{contactName(c)}</span>
                      {c.last_message_at && (
                        <time
                          className="shrink-0 text-xs text-ink-3 tabular-nums"
                          dateTime={c.last_message_at}
                        >
                          {formatListTime(c.last_message_at)}
                        </time>
                      )}
                    </div>
                    {c.last_message_preview && (
                      <p className="mt-0.5 line-clamp-1 text-sm text-ink-2">
                        {c.last_message_sender && c.last_message_sender !== "contact" && (
                          <span className="text-ink-3">
                            {SENDER_PREFIX[c.last_message_sender]}:{" "}
                          </span>
                        )}
                        {c.last_message_preview}
                      </p>
                    )}
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      {c.is_urgent && <UrgentPill />}
                      <StatusPill status={c.status} />
                      <WaitTimer conversation={c} />
                      {c.area && <span className="truncate text-xs text-ink-3">{c.area.name}</span>}
                      {c.assigned_agent && c.status !== "queued" && (
                        <span className="ml-auto truncate text-xs text-ink-3">
                          {c.assigned_agent.name}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
