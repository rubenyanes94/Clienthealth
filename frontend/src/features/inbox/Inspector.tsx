import {
  ArrowRightLeft,
  CheckCircle2,
  ExternalLink,
  PauseCircle,
  PlayCircle,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link } from "react-router";
import { useContactConsent, useConversationActions, useCopilot } from "@/api/hooks";
import type { ConversationDetail } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { displayPhone, EVENT_LABEL, formatDateTime } from "@/lib/format";
import { CloseDialog, TransferDialog } from "./CaseActions";
import { StatusPill, SurveyPill, UrgentPill, WaitTimer } from "./bits";

function Section({
  title,
  action,
  children,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="mb-7">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        {action}
      </div>
      {children}
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 px-4 py-3 text-sm">
      <dt className="text-ink-3">{label}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

function CopilotSummary({ conversationId }: { conversationId: number }) {
  const { summary } = useCopilot(conversationId);
  const toast = useToast();
  return (
    <div className="rounded-3xl bg-ai-soft p-4 ring-1 ring-inset ring-violet-600/10">
      {summary.data ? (
        <p className="text-sm leading-relaxed whitespace-pre-wrap text-ink">{summary.data.text}</p>
      ) : (
        <p className="text-sm text-ink-2">
          Resumen de la conversación para ponerse al día rápido. Los datos del paciente se
          anonimizan antes de enviarse.
        </p>
      )}
      <Button
        variant="ai"
        className="mt-3 bg-white"
        disabled={summary.isPending}
        onClick={() => summary.mutate(undefined, { onError: (e) => toast.error(e.message) })}
      >
        <Sparkles className="size-3.5" aria-hidden />
        {summary.isPending ? "Resumiendo…" : summary.data ? "Actualizar resumen" : "Resumir"}
      </Button>
    </div>
  );
}

export function Inspector({
  conversation,
  canAct,
}: {
  conversation: ConversationDetail;
  canAct: boolean;
}) {
  const { simple } = useConversationActions(conversation.id);
  const consent = useContactConsent(conversation.id);
  const toast = useToast();
  const [dialog, setDialog] = useState<"transfer" | "close" | null>(null);
  const run = (action: "pending" | "resume" | "reopen", ok: string) =>
    simple.mutate(action, {
      onSuccess: () => toast.ok(ok),
      onError: (e) => toast.error(e.message),
    });

  const status = conversation.status;
  const active = status === "open" || status === "pending";
  const recent = conversation.events.slice(-6).reverse();
  const optedIn = Boolean(conversation.contact.opt_in_at);

  return (
    <aside aria-label="Detalle del caso" className="h-full overflow-y-auto p-5 sm:p-6">
      <div className="mb-5 flex flex-wrap items-center gap-1.5">
        {conversation.is_urgent && <UrgentPill />}
        <StatusPill status={status} />
        <WaitTimer conversation={conversation} />
        {conversation.surveys.map((s) => (
          <SurveyPill key={s.id} survey={s} />
        ))}
      </div>

      {canAct && (
        <div className="mb-7 grid grid-cols-2 gap-2.5 rounded-3xl bg-surface-2 p-2.5 ring-1 ring-line ring-inset">
          {status === "open" && (
            <Button size="lg" onClick={() => run("pending", "Caso en espera del paciente")}>
              <PauseCircle className="size-4" aria-hidden /> En espera
            </Button>
          )}
          {status === "pending" && (
            <Button size="lg" onClick={() => run("resume", "Caso reanudado")}>
              <PlayCircle className="size-4" aria-hidden /> Reanudar
            </Button>
          )}
          {(active || status === "queued") && (
            <Button size="lg" onClick={() => setDialog("transfer")}>
              <ArrowRightLeft className="size-4" aria-hidden /> Transferir
            </Button>
          )}
          {status !== "closed" && status !== "bot" && (
            <Button size="lg" variant="primary" onClick={() => setDialog("close")}>
              <CheckCircle2 className="size-4" aria-hidden /> Cerrar
            </Button>
          )}
          {status === "closed" && (
            <Button size="lg" onClick={() => run("reopen", "Caso reabierto")}>
              <RotateCcw className="size-4" aria-hidden /> Reabrir
            </Button>
          )}
        </div>
      )}

      <Section title="Copiloto">
        <CopilotSummary key={conversation.id} conversationId={conversation.id} />
      </Section>

      <Section title="Caso">
        <dl className="divide-y divide-line rounded-3xl bg-surface-2 ring-1 ring-line ring-inset">
          <Row label="Teléfono">{displayPhone(conversation.contact.wa_id)}</Row>
          <Row label="Área">{conversation.area?.name ?? "—"}</Row>
          <Row label="Agente">{conversation.assigned_agent?.name ?? "Sin asignar"}</Row>
          <Row label="Prioridad">{conversation.priority === "high" ? "Alta" : "Normal"}</Row>
          <Row label="Abierta">{formatDateTime(conversation.opened_at)}</Row>
          {conversation.contact_reason && (
            <Row label="Motivo">{conversation.contact_reason.name}</Row>
          )}
        </dl>
        <label className="mt-3 flex cursor-pointer items-start gap-3 rounded-3xl p-4 text-sm ring-1 ring-line ring-inset hover:bg-surface-2">
          <input
            type="checkbox"
            className="mt-0.5 size-5 shrink-0 accent-ink"
            checked={optedIn}
            disabled={consent.isPending}
            onChange={(e) =>
              consent.mutate(
                { contactId: conversation.contact.id, optIn: e.target.checked },
                {
                  onSuccess: () =>
                    toast.ok(
                      e.target.checked ? "Consentimiento registrado" : "Consentimiento retirado",
                    ),
                  onError: (err) => toast.error(err.message),
                },
              )
            }
          />
          <span>
            <span className="font-medium">Acepta mensajes proactivos</span>
            <span className="block text-xs text-ink-3">
              {optedIn
                ? `Desde ${formatDateTime(conversation.contact.opt_in_at!)}. Puede recibir la encuesta NPS.`
                : "Márquelo solo si el paciente lo autorizó expresamente."}
            </span>
          </span>
        </label>
      </Section>

      <Section
        title="Actividad"
        action={
          <Link
            to={`/casos/${conversation.id}`}
            className="flex h-9 items-center gap-1.5 rounded-full bg-surface-3 px-3.5 text-xs font-medium text-ink-2 hover:bg-ink hover:text-white"
          >
            Registro completo <ExternalLink className="size-3" aria-hidden />
          </Link>
        }
      >
        <ol className="relative ml-1 space-y-3 border-l border-line pl-4">
          {recent.map((e) => (
            <li key={e.id} className="relative text-sm">
              <span
                className="absolute top-1.5 -left-[21px] size-2.5 rounded-full bg-ink ring-4 ring-white"
                aria-hidden
              />
              <div className="font-medium">{EVENT_LABEL[e.type]}</div>
              <div className="text-xs text-ink-3">
                {formatDateTime(e.created_at)}
                {e.agent && ` · ${e.agent.name}`}
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <TransferDialog
        conversation={conversation}
        open={dialog === "transfer"}
        onClose={() => setDialog(null)}
      />
      <CloseDialog
        conversation={conversation}
        open={dialog === "close"}
        onClose={() => setDialog(null)}
      />
    </aside>
  );
}
