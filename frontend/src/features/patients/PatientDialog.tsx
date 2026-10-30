import { useState } from "react";
import { useNavigate } from "react-router";
import { useSavePatient } from "@/api/hooks";
import type { Patient } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";
import { EMPTY_PATIENT, type PatientErrors, type PatientForm, validatePatient } from "./form";
import { PatientFields } from "./PatientFields";

function PatientFormBody({ patient, onClose }: { patient?: Patient; onClose: () => void }) {
  const save = useSavePatient(patient?.id);
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState<PatientForm>(
    patient
      ? {
          first_name: patient.first_name,
          last_name: patient.last_name,
          national_id: patient.national_id,
          phone: patient.phone,
          email: patient.email,
        }
      : EMPTY_PATIENT,
  );
  const [errors, setErrors] = useState<PatientErrors>({});

  const submit = () => {
    const found = validatePatient(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    save.mutate(form, {
      onSuccess: (saved) => {
        toast.ok(patient ? "Paciente actualizado" : "Paciente registrado");
        onClose();
        if (!patient) navigate(`/pacientes/${saved.id}`);
      },
    });
  };

  return (
    <>
      <PatientFields value={form} errors={errors} onChange={setForm} />
      {save.error && (
        <p role="alert" className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {save.error.message}
        </p>
      )}
      <div className="mt-7 grid grid-cols-2 gap-2.5">
        <Button size="lg" onClick={onClose}>
          Cancelar
        </Button>
        <Button size="lg" variant="primary" disabled={save.isPending} onClick={submit}>
          {save.isPending ? "Guardando…" : "Guardar"}
        </Button>
      </div>
    </>
  );
}

export function PatientDialog({
  open,
  onClose,
  patient,
}: {
  open: boolean;
  onClose: () => void;
  patient?: Patient;
}) {
  return (
    <Sheet
      open={open}
      onClose={onClose}
      size="lg"
      title={patient ? "Editar paciente" : "Nuevo paciente"}
      description="Todos los campos son obligatorios."
    >
      <PatientFormBody patient={patient} onClose={onClose} />
    </Sheet>
  );
}
