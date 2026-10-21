import { ArrowLeft, PanelRight } from "lucide-react";
import { Fragment, useEffect, useRef } from "react";
import { Link } from "react-router";
import { useConversationActions, useMe } from "@/api/hooks";
import type { ConversationDetail } from "@/api/types";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { dayKey, displayPhone, formatDay } from "@/lib/format";
import { StatusPill, UrgentPill } from "./bits";
import { contactName, permissionsFor } from "./permissions";
import { Composer } from "./Composer";
import { MessageBubble } from "./MessageBubble";

export function ChatView({
  conversation,
  backTo,
  onToggleInspector,
}: {
  conversation: ConversationDetail;
  backTo: string;
  onToggleInspector: () => void;
}) {
  const me = useMe();
  const toast = useToast();
  const { simple } = useConversationActions(conversation.id);
  const scroller = useRef<HTMLDivElement>(null);
  const perms = permissionsFor(conversation, me.data);
  const lastId = conversation.messages.at(-1)?.id;
  const canAccept =
    conversation.status === "queued" ||
    (conversation.status === "bot" && me.data?.role !== "agent");

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [lastId, conversation.id]);

  return (
    <section aria-label="Conversación" className="flex h-full min-h-0 flex-col">
      <header className="flex items-center gap-3 border-b border-line bg-surface px-3 py-3 sm:px-5">
        <Link
          to={backTo}
          className="rounded-lg p-1.5 text-ink-2 hover:bg-surface-3 lg:hidden"
          aria-label="Volver"
        >
          <ArrowLeft className="size-5" />
        </Link>
        <Avatar name={conversation.contact.name} urgent={conversation.is_urgent} />
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-[15px] font-semibold">{contactName(conversation)}</h2>
          <p className="truncate text-xs text-ink-3">
            {displayPhone(conversation.contact.wa_id)}
            {conversation.area && ` · ${conversation.area.name}`}
          </p>
        </div>
        <div className="hidden items-center gap-1.5 sm:flex">
          {conversation.is_urgent && <UrgentPill />}
          <StatusPill status={conversation.status} />
        </div>
        {canAccept && (
          <Button
            variant="primary"
            size="sm"
            disabled={simple.isPending}
            onClick={() =>
              simple.mutate("accept", {
                onSuccess: () => toast.ok("Caso aceptado"),
                onError: (e) => toast.error(e.message),
              })
            }
          >
            {conversation.status === "bot" ? "Intervenir" : "Aceptar"}
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleInspector}
          aria-label="Detalle del caso"
          className="xl:hidden"
        >
          <PanelRight className="size-4" />
        </Button>
      </header>

      <div ref={scroller} className="min-h-0 flex-1 space-y-2.5 overflow-y-auto px-3 py-5 sm:px-8">
        {conversation.messages.map((m, i) => {
          const prev = conversation.messages[i - 1];
          const newDay = !prev || dayKey(prev.created_at) !== dayKey(m.created_at);
          return (
            <Fragment key={m.id}>
              {newDay && (
                <div className="flex justify-center py-3">
                  <span className="rounded-full bg-surface-3 px-2.5 py-0.5 text-[11px] font-medium text-ink-3">
                    {formatDay(m.created_at)}
                  </span>
                </div>
              )}
              <MessageBubble message={m} />
            </Fragment>
          );
        })}
      </div>

      <Composer
        key={conversation.id}
        conversationId={conversation.id}
        canReply={perms.canReply}
        canNote={perms.canNote && conversation.status !== "closed"}
        blockedReason={perms.blockedReason}
      />
    </section>
  );
}
