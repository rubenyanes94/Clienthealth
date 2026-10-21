import { AlertTriangle, Clock, Star } from "lucide-react";
import type { ConversationStatus, ConversationSummary, Survey } from "@/api/types";
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

function scoreTone(survey: Survey): Tone {
  const score = survey.score ?? 0;
  if (survey.kind === "csat") return score >= 4 ? "ok" : score === 3 ? "warn" : "danger";
  return score >= 9 ? "ok" : score >= 7 ? "warn" : "danger";
}

export function SurveyPill({ survey }: { survey: Survey }) {
  const label = survey.kind === "csat" ? "CSAT" : "NPS";
  if (survey.status === "answered") {
    return (
      <Pill tone={scoreTone(survey)}>
        <Star className="size-3" aria-hidden />
        {label} {survey.score}/{survey.kind === "csat" ? 5 : 10}
      </Pill>
    );
  }
  const text = { sent: "enviada", expired: "sin respuesta", failed: "no enviada" }[survey.status];
  return (
    <Pill tone={survey.status === "failed" ? "danger" : "neutral"}>
      {label} {text}
    </Pill>
  );
}
