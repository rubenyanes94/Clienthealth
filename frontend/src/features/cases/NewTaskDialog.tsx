import clsx from "clsx";
import { useState } from "react";
import { useCatalog, useMe, useTaskActions } from "@/api/hooks";
import type { CaseDetail, CaseTaskType, Priority } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Field, invalidFieldClass } from "@/components/ui/Field";
import { Segmented } from "@/components/ui/Segmented";
import { fieldClass, Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";
import { TASK_ICON, TASK_LABEL, TASK_TYPES } from "./tasks";

const PRIORITIES: { value: Priority; label: string }[] = [
  { value: "normal", label: "Normal" },
  { value: "high", label: "Urgente" },
];

function NewTaskForm({ item, onClose }: { item: CaseDetail; onClose: () => void }) {
  const me = useMe();
  const catalog = useCatalog();
  const { create } = useTaskActions(item.id);
  const toast = useToast();
  const [type, setType] = useState<CaseTaskType>("call");
  const [assignee, setAssignee] = useState<number | "">("");
  const [priority, setPriority] = useState<Priority>("normal");
  const [notes, setNotes] = useState("");
  const [missing, setMissing] = useState(false);

  const agents = catalog.data?.agents ?? [];
  const groups = [
    ...(catalog.data?.areas ?? []).map((a) => ({
      label: a.name,
      people: agents.filter((p) => p.area_id === a.id),
    })),
    { label: "Sin área", people: agents.filter((p) => p.area_id === null) },
  ].filter((g) => g.people.length > 0);

  const submit = () => {
    if (assignee === "") {
      setMissing(true);
      return;
    }
    create.mutate(
      { type, assigned_agent_id: assignee, priority, notes },
      {
        onSuccess: () => {
          toast.ok("Tarea creada");
          onClose();
        },
      },
    );
  };

  return (
    <>
      <span className="mb-1.5 block text-sm font-medium">
        <span className="text-danger" aria-hidden>
          *{" "}
        </span>
        Tipo de tarea
      </span>
      <div role="radiogroup" aria-label="Tipo de tarea" className="mb-5 grid grid-cols-3 gap-2.5">
        {TASK_TYPES.map((t) => {
          const Icon = TASK_ICON[t];
          const active = t === type;
          return (
            <button
              key={t}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setType(t)}
              className={clsx(
                "flex h-20 flex-col items-center justify-center gap-1.5 rounded-2xl text-sm font-medium ring-1 ring-inset transition active:scale-[0.98]",
                active
                  ? "bg-ink text-white ring-ink"
                  : "bg-surface-2 text-ink-2 ring-line-strong hover:bg-surface-3",
              )}
            >
              <Icon className="size-5" aria-hidden />
              {TASK_LABEL[t]}
            </button>
          );
        })}
      </div>

      <div className="space-y-4">
        <Field
          label="Asignar a"
          htmlFor="task-assignee"
          required
          error={missing && assignee === "" ? "Complete este campo" : undefined}
        >
          <select
            id="task-assignee"
            value={assignee}
            onChange={(e) => setAssignee(e.target.value ? Number(e.target.value) : "")}
            className={clsx(fieldClass, missing && assignee === "" && invalidFieldClass)}
          >
            <option value="">Seleccione…</option>
            {groups.map((g) => (
              <optgroup key={g.label} label={g.label}>
                {g.people.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                    {p.id === me.data?.id ? " (usted)" : ""}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </Field>
        <div>
          <span className="mb-1.5 block text-sm font-medium">Prioridad</span>
          <Segmented
            label="Prioridad"
            options={PRIORITIES}
            value={priority}
            onChange={setPriority}
          />
        </div>
        <Field label="Indicaciones" htmlFor="task-notes">
          <textarea
            id="task-notes"
            rows={3}
            maxLength={1000}
            placeholder="Qué debe decirle o preguntarle al paciente…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className={`${fieldClass} h-auto py-3`}
          />
        </Field>
      </div>

      {create.error && (
        <p role="alert" className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {create.error.message}
        </p>
      )}
      <div className="mt-7 grid grid-cols-2 gap-2.5">
        <Button size="lg" onClick={onClose}>
          Cancelar
        </Button>
        <Button size="lg" variant="primary" disabled={create.isPending} onClick={submit}>
          Crear tarea
        </Button>
      </div>
    </>
  );
}

export function NewTaskDialog({
  item,
  open,
  onClose,
}: {
  item: CaseDetail;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Nueva tarea"
      description={`Caso #${item.id} · ${item.patient.first_name} ${item.patient.last_name}`}
    >
      <NewTaskForm item={item} onClose={onClose} />
    </Sheet>
  );
}
