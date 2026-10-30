import { Check, ListChecks, Plus, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { useMe, useTaskActions } from "@/api/hooks";
import type { CaseDetail, CaseTask } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Pill } from "@/components/ui/Pill";
import { useToast } from "@/components/ui/Toast";
import { patientPhone, formatDateTime } from "@/lib/format";
import { NewTaskDialog } from "./NewTaskDialog";
import { TASK_ICON, TASK_LABEL } from "./tasks";

/** Cómo contactar al paciente según la tarea. La tarea no envía nada: la hace una persona. */
function ContactLink({ task, item }: { task: CaseTask; item: CaseDetail }) {
  const className =
    "mt-2 inline-flex min-h-11 items-center rounded-full bg-surface-3 px-4 text-sm font-medium text-ink-2 transition hover:bg-ink hover:text-white";
  if (task.type === "call") {
    return (
      <a href={`tel:+${item.patient.phone}`} className={className}>
        {patientPhone(item.patient.phone)}
      </a>
    );
  }
  if (task.type === "email") {
    return (
      <a href={`mailto:${item.patient_email}`} className={`${className} max-w-full truncate`}>
        <span className="truncate">{item.patient_email}</span>
      </a>
    );
  }
  if (item.can_view_conversation) {
    return (
      <Link to={`/conversaciones/${item.conversation_id}`} className={className}>
        Abrir chat
      </Link>
    );
  }
  return <p className="mt-2 text-sm text-ink-2">{patientPhone(item.patient.phone)}</p>;
}

function PendingTask({ task, item }: { task: CaseTask; item: CaseDetail }) {
  const me = useMe();
  const { complete, cancel } = useTaskActions(item.id);
  const toast = useToast();
  const [confirming, setConfirming] = useState(false);
  const Icon = TASK_ICON[task.type];
  const busy = complete.isPending || cancel.isPending;

  return (
    <li className="rounded-2xl p-3.5 ring-1 ring-line ring-inset">
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-ink text-white">
          <Icon className="size-4" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-semibold">{TASK_LABEL[task.type]}</span>
            {task.priority === "high" && <Pill tone="danger">Urgente</Pill>}
            {task.assigned_agent.id === me.data?.id && <Pill tone="brand">Para usted</Pill>}
          </div>
          <p className="mt-0.5 text-sm text-ink-3">Asignada a {task.assigned_agent.name}</p>
          <p className="text-xs text-ink-3">
            Por {task.created_by?.name ?? "—"} · {formatDateTime(task.created_at)}
          </p>
        </div>
      </div>
      {task.notes && (
        <p className="mt-2.5 text-sm leading-relaxed break-words whitespace-pre-wrap text-ink-2">
          {task.notes}
        </p>
      )}
      <ContactLink task={task} item={item} />
      {confirming ? (
        <div className="mt-3 rounded-2xl bg-surface-2 p-3">
          <p className="mb-2 text-sm font-medium">¿Cancelar esta tarea?</p>
          <div className="grid grid-cols-2 gap-2">
            <Button onClick={() => setConfirming(false)}>No</Button>
            <Button
              variant="danger"
              disabled={busy}
              onClick={() =>
                cancel.mutate(task.id, {
                  onSuccess: () => toast.ok("Tarea cancelada"),
                  onError: (e) => toast.error(e.message),
                })
              }
            >
              Sí, cancelar
            </Button>
          </div>
        </div>
      ) : (
        <div className="mt-3 grid grid-cols-[1fr_auto] gap-2">
          <Button
            variant="primary"
            disabled={busy}
            onClick={() =>
              complete.mutate(task.id, {
                onSuccess: () => toast.ok("Tarea completada"),
                onError: (e) => toast.error(e.message),
              })
            }
          >
            <Check className="size-4" aria-hidden /> Completar
          </Button>
          <Button variant="ghost" onClick={() => setConfirming(true)}>
            Cancelar
          </Button>
        </div>
      )}
    </li>
  );
}

function FinishedTask({ task }: { task: CaseTask }) {
  const Icon = TASK_ICON[task.type];
  const done = task.status === "done";
  return (
    <li className="flex items-start gap-3 py-2.5">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-3 text-ink-3">
        <Icon className="size-3.5" aria-hidden />
      </span>
      <div className="min-w-0 flex-1 text-sm">
        <div className="flex items-center gap-1.5 font-medium">
          {done ? (
            <Check className="size-3.5 shrink-0 text-ok" aria-hidden />
          ) : (
            <X className="size-3.5 shrink-0 text-ink-3" aria-hidden />
          )}
          <span className={done ? "" : "text-ink-3 line-through"}>{TASK_LABEL[task.type]}</span>
        </div>
        <p className="text-xs text-ink-3">
          {done ? "Completada" : "Cancelada"} por {task.finished_by?.name ?? "—"}
          {task.finished_at && ` · ${formatDateTime(task.finished_at)}`}
        </p>
      </div>
    </li>
  );
}

export function TasksCard({ item }: { item: CaseDetail }) {
  const [creating, setCreating] = useState(false);
  const pending = item.tasks.filter((t) => t.status === "pending");
  const finished = item.tasks.filter((t) => t.status !== "pending").reverse();

  return (
    <section aria-label="Tareas" className="rounded-3xl bg-surface p-5 shadow-card">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <ListChecks className="size-4" aria-hidden /> Tareas ({pending.length})
        </h2>
        {item.stage !== "closed" && (
          <Button size="sm" onClick={() => setCreating(true)} className="h-11">
            <Plus className="size-4" aria-hidden /> Nueva
          </Button>
        )}
      </div>

      {pending.length === 0 && finished.length === 0 && (
        <p className="text-sm text-ink-3">
          Asigne una llamada, un WhatsApp o un correo para darle seguimiento al paciente.
        </p>
      )}
      {pending.length > 0 && (
        <ul className="space-y-2.5">
          {pending.map((t) => (
            <PendingTask key={t.id} task={t} item={item} />
          ))}
        </ul>
      )}
      {finished.length > 0 && (
        <ul className={`divide-y divide-line ${pending.length > 0 ? "mt-3" : ""}`}>
          {finished.map((t) => (
            <FinishedTask key={t.id} task={t} />
          ))}
        </ul>
      )}
      <NewTaskDialog item={item} open={creating} onClose={() => setCreating(false)} />
    </section>
  );
}
