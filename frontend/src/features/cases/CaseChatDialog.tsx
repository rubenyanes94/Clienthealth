import { Fragment } from "react";
import { useCaseConversation } from "@/api/hooks";
import { Sheet } from "@/components/ui/Sheet";
import { dayKey, formatDay } from "@/lib/format";
import { StatusPill } from "../inbox/bits";
import { MessageBubble } from "../inbox/MessageBubble";

function Transcript({ caseId }: { caseId: number }) {
  const chat = useCaseConversation(caseId);
  if (chat.isPending) return <p className="text-sm text-ink-3">Cargando…</p>;
  if (chat.error) return <p className="text-sm text-danger">{chat.error.message}</p>;
  const c = chat.data;
  return (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-2 text-sm text-ink-3">
        <StatusPill status={c.status} />
        {c.area && <span>{c.area.name}</span>}
      </div>
      <div className="max-h-[60dvh] space-y-3 overflow-y-auto rounded-3xl bg-surface-2 p-4">
        {c.messages.map((m, i) => {
          const prev = c.messages[i - 1];
          const newDay = !prev || dayKey(prev.created_at) !== dayKey(m.created_at);
          return (
            <Fragment key={m.id}>
              {newDay && (
                <div className="flex justify-center py-2">
                  <span className="rounded-full bg-surface px-3 py-1 text-xs font-medium text-ink-3 shadow-xs">
                    {formatDay(m.created_at)}
                  </span>
                </div>
              )}
              <MessageBubble message={m} />
            </Fragment>
          );
        })}
        {c.messages.length === 0 && (
          <p className="py-6 text-center text-sm text-ink-3">El chat no tiene mensajes.</p>
        )}
      </div>
      <p className="mt-3 text-xs text-ink-3">
        Solo lectura. Para responder, el chat debe estar en su área o a su nombre.
      </p>
    </>
  );
}

/** El chat del que nació el caso, en solo lectura: cualquiera que vea el caso puede leerlo. */
export function CaseChatDialog({
  caseId,
  open,
  onClose,
}: {
  caseId: number;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Sheet open={open} onClose={onClose} size="lg" title="Conversación del caso">
      <Transcript caseId={caseId} />
    </Sheet>
  );
}
