import { useState } from "react";
import { useCaseActions, useCatalog } from "@/api/hooks";
import type { CaseDetail, Priority } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Segmented } from "@/components/ui/Segmented";
import { fieldClass, Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";

type DialogProps = { item: CaseDetail; open: boolean; onClose: () => void };

function Footer({
  onClose,
  onConfirm,
  disabled,
  label,
}: {
  onClose: () => void;
  onConfirm: () => void;
  disabled: boolean;
  label: string;
}) {
  return (
    <div className="mt-7 grid grid-cols-2 gap-2.5">
      <Button size="lg" onClick={onClose}>
        Cancelar
      </Button>
      <Button size="lg" variant="primary" disabled={disabled} onClick={onConfirm}>
        {label}
      </Button>
    </div>
  );
}

export function TransferCaseDialog({ item, open, onClose }: DialogProps) {
  const catalog = useCatalog();
  const { transfer } = useCaseActions(item.id);
  const toast = useToast();
  const [areaId, setAreaId] = useState<number | "">("");
  const areas = catalog.data?.areas.filter((a) => a.id !== item.area.id) ?? [];

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Transferir a otra área"
      description="El caso queda por atender en esa área, sin responsable, hasta que alguien lo tome."
    >
      <Field label="Área" htmlFor="case-transfer-area" required>
        <select
          id="case-transfer-area"
          className={fieldClass}
          value={areaId}
          onChange={(e) => setAreaId(e.target.value ? Number(e.target.value) : "")}
        >
          <option value="">Seleccione…</option>
          {areas.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </Field>
      <Footer
        onClose={onClose}
        label="Transferir"
        disabled={!areaId || transfer.isPending}
        onConfirm={() =>
          areaId &&
          transfer.mutate(areaId, {
            onSuccess: () => {
              toast.ok("Caso transferido");
              onClose();
            },
            onError: (e) => toast.error(e.message),
          })
        }
      />
    </Sheet>
  );
}

export function CloseCaseDialog({ item, open, onClose }: DialogProps) {
  const catalog = useCatalog();
  const { stage } = useCaseActions(item.id);
  const toast = useToast();
  const [reasonId, setReasonId] = useState<number | "">(item.contact_reason?.id ?? "");
  const reasons =
    catalog.data?.reasons.filter((r) => r.area_id === null || r.area_id === item.area.id) ?? [];

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Cerrar caso"
      description="El motivo es obligatorio: alimenta los indicadores."
    >
      <Field label="Motivo de contacto" htmlFor="case-close-reason" required>
        <select
          id="case-close-reason"
          className={fieldClass}
          value={reasonId}
          onChange={(e) => setReasonId(e.target.value ? Number(e.target.value) : "")}
        >
          <option value="">Seleccione el motivo…</option>
          {reasons.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </Field>
      <Footer
        onClose={onClose}
        label="Cerrar caso"
        disabled={!reasonId || stage.isPending}
        onConfirm={() =>
          reasonId &&
          stage.mutate(
            { stage: "closed", contact_reason_id: reasonId },
            {
              onSuccess: () => {
                toast.ok("Caso cerrado");
                onClose();
              },
              onError: (e) => toast.error(e.message),
            },
          )
        }
      />
    </Sheet>
  );
}

const PRIORITIES: { value: Priority; label: string }[] = [
  { value: "normal", label: "Normal" },
  { value: "high", label: "Urgente" },
];

function EditCaseForm({ item, onClose }: { item: CaseDetail; onClose: () => void }) {
  const { update } = useCaseActions(item.id);
  const toast = useToast();
  const [subject, setSubject] = useState(item.subject);
  const [description, setDescription] = useState(item.description);
  const [priority, setPriority] = useState<Priority>(item.priority);

  return (
    <>
      <div className="space-y-4">
        <Field label="Asunto" htmlFor="case-edit-subject" required>
          <input
            id="case-edit-subject"
            maxLength={200}
            className={fieldClass}
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        </Field>
        <Field label="Descripción" htmlFor="case-edit-description">
          <textarea
            id="case-edit-description"
            rows={4}
            maxLength={4000}
            className={`${fieldClass} h-auto py-3`}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
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
      </div>
      <Footer
        onClose={onClose}
        label="Guardar"
        disabled={subject.trim().length < 3 || update.isPending}
        onConfirm={() =>
          update.mutate(
            { subject: subject.trim(), description: description.trim(), priority },
            {
              onSuccess: () => {
                toast.ok("Caso actualizado");
                onClose();
              },
              onError: (e) => toast.error(e.message),
            },
          )
        }
      />
    </>
  );
}

export function EditCaseDialog({ item, open, onClose }: DialogProps) {
  return (
    <Sheet open={open} onClose={onClose} title="Editar caso">
      <EditCaseForm item={item} onClose={onClose} />
    </Sheet>
  );
}
