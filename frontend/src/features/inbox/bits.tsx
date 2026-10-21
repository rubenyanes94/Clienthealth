import { AlertTriangle, Clock } from "lucide-react";
import type { ConversationStatus, ConversationSummary } from "@/api/types";
import { Pill, type Tone } from "@/components/ui/Pill";
import { formatElapsed, STATUS_LABEL } from "@/lib/format";
import { useNow } from "@/lib/useNow";

const STATUS_TONE: Record<ConversationStatus, Tone> = {
  bot: "neutral",
  queued: "warn",
  open: "brand",
  pending: "note",
  closed: "neutral",
};

export function StatusPill({ status }: { status: ConversationStatus }) {
  return <Pill tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Pill>;
}

export function UrgentPill() {
  return (
    <Pill tone="danger">
      <AlertTriangle className="size-3" aria-hidden /> Urgente
    </Pill>
  );
}

/** Espera en cola contra la meta de 1ª respuesta del área. Corre en el cliente. */
export function WaitTimer({ conversation }: { conversation: ConversationSummary }) {
  const now = useNow();
  if (conversation.status !== "queued" || !conversation.queued_at) return null;
  const goalMs = (conversation.area?.sla_first_response_minutes ?? 15) * 60_000;
  const waited = now - new Date(conversation.queued_at).getTime();
  const tone: Tone = waited >= goalMs ? "danger" : waited >= goalMs * 0.75 ? "warn" : "ok";
  return (
    <Pill tone={tone}>
      <Clock className="size-3" aria-hidden />
      <span className="tabular-nums">{formatElapsed(conversation.queued_at, now)}</span>
    </Pill>
  );
}
