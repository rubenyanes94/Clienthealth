import {
  ArrowLeft,
  ArrowRightLeft,
  ChevronRight,
  Hand,
  MessagesSquare,
  Pencil,
  SendHorizontal,
  User,
  UserPlus,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router";
import { useCase, useCaseActions, useCatalog, useMe } from "@/api/hooks";
import type { CaseDetail, CaseEvent, CaseStage, CaseTaskType } from "@/api/types";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { NotificationBell } from "@/features/notifications/NotificationCenter";
import { Pill } from "@/components/ui/Pill";
import { Segmented } from "@/components/ui/Segmented";
import { useToast } from "@/components/ui/Toast";
import { patientPhone, formatDateTime } from "@/lib/format";
import {
  AssignCaseDialog,
  CloseCaseDialog,
  EditCaseDialog,
  TransferCaseDialog,
} from "./CaseDialogs";
import { StagePath } from "./StagePath";
import { STAGE_LABEL, stepLabel } from "./stages";
import { TASK_LABEL } from "./tasks";
import { TasksCard } from "./TasksCard";

type Tab = "detalles" | "notas" | "actividad";

const FIELD_LABEL: Record<string, string> = {
  subject: "asunto",
  description: "descripción",
  priority: "prioridad",
};

function useEventText() {
  const catalog = useCatalog();
  const areaName = (id: unknown) =>
    catalog.data?.areas.find((a) => a.id === id)?.name ?? `Área ${String(id)}`;
  return (event: CaseEvent): string => {
    const d = event.data;
    switch (event.type) {
      case "created":
        return `Caso creado en ${areaName(d.area_id)}`;
      case "stage_changed":
        return `De ${STAGE_LABEL[d.from as CaseStage]} a ${STAGE_LABEL[d.to as CaseStage]}`;
      case "transferred":
        return `Transferido de ${areaName(d.from_area_id)} a ${areaName(d.to_area_id)}`;
      case "taken":
        return "Caso tomado";
      case "assigned": {
        const person = catalog.data?.agents.find((a) => a.id === d.assigned_agent_id)?.name;
        return person ? `Caso asignado a ${person}` : "Caso asignado";
      }
      case "updated": {
        const fields = (d.fields as string[]).map((f) => FIELD_LABEL[f] ?? f);
        return `Editado: ${fields.join(", ")}`;
      }
      case "note_added":
        return "Nota agregada";
      case "task_created": {
        const person = catalog.data?.agents.find((a) => a.id === d.assigned_agent_id)?.name;
        const label = TASK_LABEL[d.task_type as CaseTaskType];
        return person ? `Tarea «${label}» asignada a ${person}` : `Tarea «${label}» creada`;
      }
      case "task_completed":
        return `Tarea «${TASK_LABEL[d.task_type as CaseTaskType]}» completada`;
      case "task_cancelled":
        return `Tarea «${TASK_LABEL[d.task_type as CaseTaskType]}» cancelada`;
    }
  };
}

function Info({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-line py-3 text-sm last:border-0">
      <dt className="text-ink-3">{label}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

function StageActions({ item, onClose }: { item: CaseDetail; onClose: () => void }) {
  const { stage } = useCaseActions(item.id);
  const toast = useToast();
  const go = (to: CaseStage) => {
    if (to === "closed") return onClose();
    stage.mutate(
      { stage: to },
      {
        onSuccess: () => toast.ok(`Caso: ${STAGE_LABEL[to]}`),
        onError: (e) => toast.error(e.message),
      },
    );
  };
  return (
    <div className="flex shrink-0 flex-wrap gap-2">
      {item.next_stages.map((to, i) => (
        <Button
          key={to}
          size="lg"
          variant={i === 0 ? "primary" : "secondary"}
          disabled={stage.isPending}
          onClick={() => go(to)}
        >
          {stepLabel(item.stage, to)}
        </Button>
      ))}
    </div>
  );
}

function Notes({ item }: { item: CaseDetail }) {
  const { note } = useCaseActions(item.id);
  const toast = useToast();
  const [body, setBody] = useState("");
  const submit = () => {
    if (!body.trim()) return;
    note.mutate(body, {
      onSuccess: () => setBody(""),
      onError: (e) => toast.error(e.message),
    });
  };
  return (
    <>
      <div className="mb-5 flex items-end gap-2 rounded-3xl bg-surface-2 p-2 ring-1 ring-line-strong ring-inset focus-within:bg-surface focus-within:ring-2 focus-within:ring-ink">
        <label className="sr-only" htmlFor="case-note">
          Nueva nota
        </label>
        <textarea
          id="case-note"
          rows={2}
          maxLength={4000}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Escriba una nota para el equipo…"
          className="min-h-12 flex-1 resize-none bg-transparent px-3 py-2 text-base outline-none placeholder:text-ink-3"
        />
        <Button
          variant="primary"
          className="size-12 px-0"
          aria-label="Guardar nota"
          disabled={!body.trim() || note.isPending}
          onClick={submit}
        >
          <SendHorizontal className="size-5" aria-hidden />
        </Button>
      </div>
      {item.notes.length === 0 ? (
        <p className="py-6 text-center text-sm text-ink-3">Aún no hay notas.</p>
      ) : (
        <ul className="space-y-3">
          {[...item.notes].reverse().map((n) => (
            <li key={n.id} className="rounded-2xl bg-surface-2 p-4">
              <p className="text-[15px] leading-relaxed break-words whitespace-pre-wrap">
                {n.body}
              </p>
              <p className="mt-2 text-xs text-ink-3">
                {n.agent?.name ?? "—"} · {formatDateTime(n.created_at)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function Activity({ item }: { item: CaseDetail }) {
  const textOf = useEventText();
  return (
    <ol className="relative ml-2 border-l border-line">
      {[...item.events].reverse().map((e) => (
        <li key={e.id} className="mb-5 ml-6">
          <span
            className="absolute -left-[5px] mt-1.5 size-2.5 rounded-full bg-ink ring-4 ring-white"
            aria-hidden
          />
          <div className="text-sm font-medium">{textOf(e)}</div>
          <div className="text-xs text-ink-3">
            {formatDateTime(e.created_at)}
            {e.agent && ` · ${e.agent.name}`}
          </div>
        </li>
      ))}
    </ol>
  );
}

export function CaseDetailPage() {
  const id = Number(useParams().id);
  const query = useCase(id);
  const me = useMe();
  const toast = useToast();
  const { take } = useCaseActions(id);
  const [tab, setTab] = useState<Tab>("detalles");
  const [dialog, setDialog] = useState<"transfer" | "close" | "edit" | "assign" | null>(null);
  const c = query.data;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl px-3 py-3 sm:px-4 md:py-0">
        <div className="mb-4 flex items-center justify-between gap-3">
          <Link
            to="/casos"
            className="inline-flex h-11 items-center gap-2 rounded-full bg-surface px-5 text-sm font-medium text-ink-2 shadow-card transition hover:text-ink"
          >
            <ArrowLeft className="size-4" aria-hidden /> Casos
          </Link>
          <NotificationBell />
        </div>
        {query.error && <p className="text-sm text-danger">{query.error.message}</p>}
        {c && (
          <>
            <header className="mb-3 rounded-3xl bg-surface p-6 shadow-card">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm text-ink-3">Caso #{c.id}</p>
                  <h1 className="text-3xl font-bold break-words">{c.subject}</h1>
                </div>
                {c.stage !== "closed" && (
                  <div className="flex flex-wrap gap-2">
                    {c.assigned_agent?.id !== me.data?.id && (
                      <Button
                        disabled={take.isPending}
                        onClick={() =>
                          take.mutate(undefined, {
                            onSuccess: () => toast.ok("Caso tomado"),
                            onError: (e) => toast.error(e.message),
                          })
                        }
                      >
                        <Hand className="size-4" aria-hidden /> Tomar caso
                      </Button>
                    )}
                    <Button onClick={() => setDialog("assign")}>
                      <UserPlus className="size-4" aria-hidden /> Asignar
                    </Button>
                    {c.stage !== "resolved" && (
                      <Button onClick={() => setDialog("transfer")}>
                        <ArrowRightLeft className="size-4" aria-hidden /> Transferir
                      </Button>
                    )}
                    <Button onClick={() => setDialog("edit")}>
                      <Pencil className="size-4" aria-hidden /> Editar
                    </Button>
                  </div>
                )}
              </div>
              <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-5 lg:grid-cols-5">
                {(
                  [
                    ["Paciente", `${c.patient.first_name} ${c.patient.last_name}`],
                    ["Área", c.area.name],
                    ["Responsable", c.assigned_agent?.name ?? "Sin asignar"],
                    ["Abierto", formatDateTime(c.opened_at)],
                    ["Origen", c.conversation_id ? "WhatsApp" : "Presencial"],
                  ] as const
                ).map(([label, value]) => (
                  <div key={label} className="min-w-0">
                    <dt className="text-xs text-ink-3">{label}</dt>
                    <dd className="mt-1 truncate text-[15px] font-medium">{value}</dd>
                  </div>
                ))}
              </dl>
            </header>

            <div className="mb-3 flex flex-wrap items-center gap-3 rounded-3xl bg-surface p-3 shadow-card">
              <div className="w-full xl:w-auto xl:min-w-0 xl:flex-1">
                <StagePath stage={c.stage} events={c.events} />
              </div>
              <div className="ml-auto">
                <StageActions item={c} onClose={() => setDialog("close")} />
              </div>
            </div>

            <div className="mb-3 grid items-start gap-3 lg:grid-cols-[minmax(0,1fr)_22rem]">
              <section className="rounded-3xl bg-surface p-5 shadow-card sm:p-6">
                <div className="mb-5 flex">
                  <Segmented
                    label="Sección del caso"
                    value={tab}
                    onChange={setTab}
                    options={[
                      { value: "detalles", label: "Detalles" },
                      { value: "notas", label: "Notas", count: c.notes.length },
                      { value: "actividad", label: "Actividad" },
                    ]}
                  />
                </div>
                {tab === "detalles" && (
                  <>
                    <dl className="grid gap-x-10 md:grid-cols-2">
                      <div>
                        <Info label="Prioridad">
                          {c.priority === "high" ? <Pill tone="danger">Urgente</Pill> : "Normal"}
                        </Info>
                        <Info label="Etapa">{STAGE_LABEL[c.stage]}</Info>
                        <Info label="Motivo">{c.contact_reason?.name ?? "—"}</Info>
                      </div>
                      <div>
                        <Info label="Creado por">{c.created_by?.name ?? "—"}</Info>
                        <Info label="Resuelto">
                          {c.resolved_at ? formatDateTime(c.resolved_at) : "—"}
                        </Info>
                        <Info label="Cerrado">
                          {c.closed_at ? formatDateTime(c.closed_at) : "—"}
                        </Info>
                      </div>
                    </dl>
                    <h2 className="mt-6 mb-2 text-sm font-semibold">Descripción</h2>
                    <p className="text-[15px] leading-relaxed break-words whitespace-pre-wrap text-ink-2">
                      {c.description || "Sin descripción."}
                    </p>
                  </>
                )}
                {tab === "notas" && <Notes item={c} />}
                {tab === "actividad" && <Activity item={c} />}
              </section>

              <aside className="space-y-3">
                <Link
                  to={`/pacientes/${c.patient.id}`}
                  className="block rounded-3xl bg-surface p-5 shadow-card transition hover:bg-surface-2"
                >
                  <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                    <User className="size-4" aria-hidden /> Paciente
                  </h2>
                  <div className="flex items-center gap-3">
                    <Avatar name={`${c.patient.first_name} ${c.patient.last_name}`} />
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-semibold">
                        {c.patient.first_name} {c.patient.last_name}
                      </div>
                      <div className="truncate text-sm text-ink-3">{c.patient.national_id}</div>
                      <div className="truncate text-sm text-ink-3">
                        {patientPhone(c.patient.phone)}
                      </div>
                    </div>
                    <ChevronRight className="size-4 shrink-0 text-ink-3" aria-hidden />
                  </div>
                </Link>
                <TasksCard item={c} />
                {c.conversation_id !== null && (
                  <div className="rounded-3xl bg-surface p-5 shadow-card">
                    <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold">
                      <MessagesSquare className="size-4" aria-hidden /> Conversación
                    </h2>
                    {c.can_view_conversation ? (
                      <Link
                        to={`/conversaciones/${c.conversation_id}`}
                        className="inline-flex h-11 items-center gap-2 rounded-full bg-surface-3 px-5 text-sm font-medium text-ink-2 transition hover:bg-ink hover:text-white"
                      >
                        Abrir chat
                      </Link>
                    ) : (
                      <p className="text-sm text-ink-3">
                        Creado desde un chat que está asignado a otra persona o área.
                      </p>
                    )}
                  </div>
                )}
              </aside>
            </div>

            <TransferCaseDialog
              item={c}
              open={dialog === "transfer"}
              onClose={() => setDialog(null)}
            />
            <AssignCaseDialog item={c} open={dialog === "assign"} onClose={() => setDialog(null)} />
            <CloseCaseDialog item={c} open={dialog === "close"} onClose={() => setDialog(null)} />
            <EditCaseDialog item={c} open={dialog === "edit"} onClose={() => setDialog(null)} />
          </>
        )}
      </div>
    </div>
  );
}
