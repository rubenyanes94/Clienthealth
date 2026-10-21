import {
  ArrowRightLeft,
  CheckCircle2,
  ExternalLink,
  PauseCircle,
  PlayCircle,
  RotateCcw,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link } from "react-router";
import { useConversationActions } from "@/api/hooks";
import type { ConversationDetail } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { displayPhone, EVENT_LABEL, formatDateTime } from "@/lib/format";
import { CloseDialog, TransferDialog } from "./CaseActions";
import { StatusPill, UrgentPill, WaitTimer } from "./bits";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 py-1.5 text-sm">
      <dt className="text-ink-3">{label}</dt>
      <dd className="text-right font-medium">{children}</dd>
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

  return (
    <aside aria-label="Detalle del caso" className="h-full overflow-y-auto p-4">
      <div className="mb-4 flex flex-wrap items-center gap-1.5">
        {conversation.is_urgent && <UrgentPill />}
        <StatusPill status={status} />
        <WaitTimer conversation={conversation} />
      </div>

      <dl className="mb-4 divide-y divide-line rounded-card border border-line bg-surface px-3">
        <Row label="Teléfono">{displayPhone(conversation.contact.wa_id)}</Row>
        <Row label="Área">{conversation.area?.name ?? "—"}</Row>
        <Row label="Agente">{conversation.assigned_agent?.name ?? "Sin asignar"}</Row>
        <Row label="Prioridad">{conversation.priority === "high" ? "Alta" : "Normal"}</Row>
        <Row label="Abierta">{formatDateTime(conversation.opened_at)}</Row>
        {conversation.contact_reason && (
          <Row label="Motivo">{conversation.contact_reason.name}</Row>
        )}
      </dl>

      {canAct && (
        <div className="mb-5 grid grid-cols-2 gap-2">
          {status === "open" && (
            <Button size="sm" onClick={() => run("pending", "Caso en espera del paciente")}>
              <PauseCircle className="size-4" aria-hidden /> En espera
            </Button>
          )}
          {status === "pending" && (
            <Button size="sm" onClick={() => run("resume", "Caso reanudado")}>
              <PlayCircle className="size-4" aria-hidden /> Reanudar
            </Button>
          )}
          {(active || status === "queued") && (
            <Button size="sm" onClick={() => setDialog("transfer")}>
              <ArrowRightLeft className="size-4" aria-hidden /> Transferir
            </Button>
          )}
          {status !== "closed" && status !== "bot" && (
            <Button size="sm" variant="primary" onClick={() => setDialog("close")}>
              <CheckCircle2 className="size-4" aria-hidden /> Cerrar
            </Button>
          )}
          {status === "closed" && (
            <Button size="sm" onClick={() => run("reopen", "Caso reabierto")}>
              <RotateCcw className="size-4" aria-hidden /> Reabrir
            </Button>
          )}
        </div>
      )}

      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold tracking-wide text-ink-3 uppercase">Actividad</h3>
        <Link
          to={`/casos/${conversation.id}`}
          className="flex items-center gap-1 text-xs font-medium text-brand hover:underline"
        >
          Registro completo <ExternalLink className="size-3" aria-hidden />
        </Link>
      </div>
      <ol className="space-y-2">
        {recent.map((e) => (
          <li key={e.id} className="text-sm">
            <div className="font-medium">{EVENT_LABEL[e.type]}</div>
            <div className="text-xs text-ink-3">
              {formatDateTime(e.created_at)}
              {e.agent && ` · ${e.agent.name}`}
            </div>
          </li>
        ))}
      </ol>

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
