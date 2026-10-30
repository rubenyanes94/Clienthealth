import clsx from "clsx";
import { Search, UserPlus, X } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";
import { useCatalog, useCreateCase, useMe, usePatientSearch, useSavePatient } from "@/api/hooks";
import type { ConversationDetail, PatientRef, Priority } from "@/api/types";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Field, invalidFieldClass } from "@/components/ui/Field";
import { Segmented } from "@/components/ui/Segmented";
import { fieldClass, Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";
import { displayPhone } from "@/lib/format";
import { useDebounced } from "@/lib/useDebounced";
import {
  EMPTY_PATIENT,
  type PatientErrors,
  type PatientForm,
  splitName,
  validatePatient,
} from "../patients/form";
import { PatientFields } from "../patients/PatientFields";

const PRIORITIES: { value: Priority; label: string }[] = [
  { value: "normal", label: "Normal" },
  { value: "high", label: "Urgente" },
];

function NewCaseForm({
  onClose,
  conversation,
  patient: presetPatient,
}: {
  onClose: () => void;
  conversation?: ConversationDetail;
  patient?: PatientRef;
}) {
  const navigate = useNavigate();
  const toast = useToast();
  const me = useMe();
  const catalog = useCatalog();
  const createCase = useCreateCase();
  const savePatient = useSavePatient();

  const [patient, setPatient] = useState<PatientRef | null>(
    presetPatient ?? conversation?.patient ?? null,
  );
  // Desde un chat se busca de entrada por su número: normalmente ya está registrado.
  const [q, setQ] = useState(conversation ? conversation.contact.wa_id : "");
  const [registering, setRegistering] = useState(false);
  const [patientForm, setPatientForm] = useState<PatientForm>(
    conversation
      ? {
          ...EMPTY_PATIENT,
          ...splitName(conversation.contact.name),
          phone: conversation.contact.wa_id,
        }
      : EMPTY_PATIENT,
  );
  const [patientErrors, setPatientErrors] = useState<PatientErrors>({});
  const results = usePatientSearch(useDebounced(q));

  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Priority>(conversation?.is_urgent ? "high" : "normal");
  const [areaChoice, setAreaChoice] = useState<number | "">("");
  const [errors, setErrors] = useState<{ subject?: string; area?: string; patient?: string }>({});

  const areas = catalog.data?.areas ?? [];
  const suggestedArea =
    conversation?.area?.id ??
    me.data?.area_id ??
    areas.find((a) => a.is_default)?.id ??
    areas[0]?.id;
  const areaId = areaChoice === "" ? (suggestedArea ?? "") : areaChoice;
  const busy = createCase.isPending || savePatient.isPending;

  const submit = async () => {
    const found: typeof errors = {};
    if (subject.trim().length < 3) found.subject = "Complete este campo";
    if (areaId === "") found.area = "Elija un área";
    const foundPatient = registering ? validatePatient(patientForm) : {};
    if (!patient && !registering) found.patient = "Elija un paciente o registre uno nuevo";
    setErrors(found);
    setPatientErrors(foundPatient);
    if (Object.keys(found).length > 0 || Object.keys(foundPatient).length > 0) return;

    try {
      // Si el paciente se guarda y el caso falla, queda elegido: reintentar no lo duplica.
      let target = patient;
      if (!target) {
        target = await savePatient.mutateAsync(patientForm);
        setPatient(target);
        setRegistering(false);
      }
      const created = await createCase.mutateAsync({
        patient_id: target.id,
        area_id: areaId as number,
        subject: subject.trim(),
        description,
        priority,
        conversation_id: conversation?.id ?? null,
      });
      toast.ok(`Caso #${created.id} creado`);
      onClose();
      if (!conversation) navigate(`/casos/${created.id}`);
    } catch {
      // El mensaje del backend se muestra abajo, junto a los botones.
    }
  };

  const failure = savePatient.error ?? createCase.error;

  return (
    <>
      <section aria-label="Paciente" className="rounded-3xl bg-surface-2 p-4 sm:p-5">
        <h3 className="mb-3 text-sm font-semibold">Paciente</h3>
        {patient ? (
          <div className="flex items-center gap-3 rounded-2xl bg-surface p-3 shadow-xs">
            <Avatar name={`${patient.first_name} ${patient.last_name}`} />
            <div className="min-w-0 flex-1">
              <div className="truncate font-semibold">
                {patient.first_name} {patient.last_name}
              </div>
              <div className="truncate text-sm text-ink-3">
                {patient.national_id} · {displayPhone(patient.phone)}
              </div>
            </div>
            {!presetPatient && (
              <Button variant="ghost" onClick={() => setPatient(null)}>
                <X className="size-4" aria-hidden /> Cambiar
              </Button>
            )}
          </div>
        ) : registering ? (
          <>
            <PatientFields value={patientForm} errors={patientErrors} onChange={setPatientForm} />
            <Button variant="ghost" className="mt-3" onClick={() => setRegistering(false)}>
              <Search className="size-4" aria-hidden /> Buscar un paciente registrado
            </Button>
          </>
        ) : (
          <>
            <div className="relative">
              <Search
                className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-ink-3"
                aria-hidden
              />
              <label className="sr-only" htmlFor="case-patient-search">
                Buscar paciente
              </label>
              <input
                id="case-patient-search"
                type="search"
                autoComplete="off"
                placeholder="Nombre, cédula o teléfono…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className={`${fieldClass} bg-surface pl-12`}
              />
            </div>
            <ul className="mt-2 max-h-52 space-y-1 overflow-y-auto">
              {results.data?.items.slice(0, 20).map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => setPatient(p)}
                    className="flex w-full items-center gap-3 rounded-2xl p-2.5 text-left transition hover:bg-surface active:bg-surface-3"
                  >
                    <Avatar name={`${p.first_name} ${p.last_name}`} size="sm" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold">
                        {p.first_name} {p.last_name}
                      </span>
                      <span className="block truncate text-xs text-ink-3">
                        {p.national_id} · {displayPhone(p.phone)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {results.data?.items.length === 0 && (
              <p className="py-3 text-center text-sm text-ink-3">
                {q ? "Ningún paciente coincide." : "Aún no hay pacientes registrados."}
              </p>
            )}
            <Button className="mt-2 w-full" onClick={() => setRegistering(true)}>
              <UserPlus className="size-4" aria-hidden /> Registrar paciente nuevo
            </Button>
            {errors.patient && (
              <p role="alert" className="mt-2 text-sm text-danger">
                {errors.patient}
              </p>
            )}
          </>
        )}
      </section>

      <section aria-label="Información del caso" className="mt-5">
        <h3 className="mb-3 text-sm font-semibold">Información del caso</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Asunto" htmlFor="case-subject" required error={errors.subject}>
            <input
              id="case-subject"
              maxLength={200}
              autoComplete="off"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              aria-invalid={Boolean(errors.subject)}
              className={clsx(fieldClass, errors.subject && invalidFieldClass)}
            />
          </Field>
          <Field label="Área responsable" htmlFor="case-area-new" required error={errors.area}>
            <select
              id="case-area-new"
              value={areaId}
              onChange={(e) => setAreaChoice(e.target.value ? Number(e.target.value) : "")}
              className={clsx(fieldClass, errors.area && invalidFieldClass)}
            >
              <option value="">Seleccione…</option>
              {areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Descripción" htmlFor="case-description">
            <textarea
              id="case-description"
              rows={3}
              maxLength={4000}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className={`${fieldClass} h-auto py-3`}
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
      </section>

      {failure && (
        <p role="alert" className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {failure.message}
        </p>
      )}

      <div className="sticky bottom-0 -mx-7 -mb-7 mt-6 flex justify-end gap-2.5 border-t border-line bg-surface px-7 py-4">
        <Button size="lg" onClick={onClose}>
          Cancelar
        </Button>
        <Button size="lg" variant="primary" disabled={busy} onClick={submit}>
          {busy ? "Creando…" : "Crear caso"}
        </Button>
      </div>
    </>
  );
}

/** Crear un caso. Con `conversation` queda vinculado al chat; con `patient`, el paciente va fijo. */
export function NewCaseDialog({
  open,
  onClose,
  conversation,
  patient,
}: {
  open: boolean;
  onClose: () => void;
  conversation?: ConversationDetail;
  patient?: PatientRef;
}) {
  return (
    <Sheet open={open} onClose={onClose} size="lg" title="Nuevo caso">
      <NewCaseForm onClose={onClose} conversation={conversation} patient={patient} />
    </Sheet>
  );
}
