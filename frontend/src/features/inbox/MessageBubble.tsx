import clsx from "clsx";
import { AlertCircle, Check, CheckCheck, FlaskConical, Lock } from "lucide-react";
import type { Message } from "@/api/types";
import { formatTime } from "@/lib/format";

function DeliveryIcon({ status }: { status: Message["status"] }) {
  switch (status) {
    case "sent":
      return <Check className="size-3.5" aria-label="Enviado" />;
    case "delivered":
      return <CheckCheck className="size-3.5" aria-label="Entregado" />;
    case "read":
      return <CheckCheck className="size-3.5 text-brand" aria-label="Leído" />;
    case "failed":
      return <AlertCircle className="size-3.5 text-danger" aria-label="No se pudo enviar" />;
    case "simulated":
      return <FlaskConical className="size-3.5" aria-label="Simulado (sin envío real)" />;
    default:
      return null;
  }
}

const SENDER_LABEL: Record<Message["sender_type"], string> = {
  contact: "",
  bot: "Bot",
  system: "Mensaje automático",
  agent: "",
};

export function MessageBubble({ message }: { message: Message }) {
  const inbound = message.direction === "inbound";
  const note = message.is_internal_note;
  const automated = message.sender_type === "bot" || message.sender_type === "system";
  const author = message.agent?.name ?? SENDER_LABEL[message.sender_type];

  return (
    <div className={clsx("flex", inbound ? "justify-start" : "justify-end")}>
      <div
        className={clsx(
          "max-w-[85%] rounded-2xl px-3.5 py-2 text-sm shadow-card sm:max-w-[70%]",
          inbound && "rounded-bl-md bg-surface",
          !inbound && !note && !automated && "rounded-br-md bg-brand-soft",
          automated && "rounded-br-md border border-dashed border-line bg-surface-2",
          note && "rounded-br-md border border-note/30 bg-note-soft",
        )}
      >
        {(author || note) && (
          <div className="mb-0.5 flex items-center gap-1 text-xs font-medium text-ink-3">
            {note && <Lock className="size-3" aria-hidden />}
            {note ? `Nota interna · ${author}` : author}
          </div>
        )}
        <p className="break-words whitespace-pre-wrap">{message.body}</p>
        <div className="mt-1 flex items-center justify-end gap-1 text-[11px] text-ink-3">
          <time dateTime={message.created_at}>{formatTime(message.created_at)}</time>
          {!inbound && !note && <DeliveryIcon status={message.status} />}
        </div>
      </div>
    </div>
  );
}
