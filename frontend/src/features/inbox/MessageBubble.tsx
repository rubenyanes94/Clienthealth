import clsx from "clsx";
import { AlertCircle, Bot, Check, CheckCheck, FlaskConical, Lock } from "lucide-react";
import type { Message } from "@/api/types";
import { formatTime } from "@/lib/format";

function DeliveryIcon({ status }: { status: Message["status"] }) {
  switch (status) {
    case "sent":
      return <Check className="size-3.5" aria-label="Enviado" />;
    case "delivered":
      return <CheckCheck className="size-3.5" aria-label="Entregado" />;
    case "read":
      return <CheckCheck className="size-3.5 text-sky-400" aria-label="Leído" />;
    case "failed":
      return <AlertCircle className="size-3.5 text-danger" aria-label="No se pudo enviar" />;
    case "simulated":
      return <FlaskConical className="size-3.5" aria-label="Simulado (sin envío real)" />;
    default:
      return null;
  }
}

export function MessageBubble({ message }: { message: Message }) {
  const inbound = message.direction === "inbound";
  const note = message.is_internal_note;
  const automated = message.sender_type === "bot" || message.sender_type === "system";
  const agentReply = !inbound && !note && !automated;
  const author = note
    ? `Nota interna · ${message.agent?.name ?? ""}`
    : automated
      ? message.message_type === "template"
        ? "Plantilla"
        : message.sender_type === "bot"
          ? "Bot"
          : "Mensaje automático"
      : (message.agent?.name ?? null);

  return (
    <div className={clsx("flex", inbound ? "justify-start" : "justify-end")}>
      <div
        className={clsx(
          "max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[14px] leading-relaxed sm:max-w-[68%]",
          inbound && "rounded-bl-md bg-surface-3 text-ink",
          agentReply && "rounded-br-md bg-ink text-white shadow-card",
          automated && "rounded-br-md bg-surface text-ink-2 ring-1 ring-line ring-inset",
          note && "rounded-br-md bg-note-soft text-ink ring-1 ring-yellow-600/20 ring-inset",
        )}
      >
        {author && (
          <div
            className={clsx(
              "mb-0.5 flex items-center gap-1 text-[11px] font-semibold",
              agentReply ? "text-white/60" : note ? "text-note" : "text-ink-3",
            )}
          >
            {note && <Lock className="size-3" aria-hidden />}
            {automated && <Bot className="size-3" aria-hidden />}
            {author}
          </div>
        )}
        <p className="break-words whitespace-pre-wrap">{message.body}</p>
        <div
          className={clsx(
            "mt-1 flex items-center justify-end gap-1 text-[11px] tabular-nums",
            agentReply ? "text-white/60" : "text-ink-3",
          )}
        >
          <time dateTime={message.created_at}>{formatTime(message.created_at)}</time>
          {!inbound && !note && <DeliveryIcon status={message.status} />}
        </div>
      </div>
    </div>
  );
}
