import clsx from "clsx";
import { Field, invalidFieldClass } from "@/components/ui/Field";
import { fieldClass } from "@/components/ui/Sheet";
import type { PatientErrors, PatientForm } from "./form";

const FIELDS: {
  name: keyof PatientForm;
  label: string;
  type: string;
  placeholder?: string;
  autoComplete: string;
}[] = [
  { name: "first_name", label: "Nombre", type: "text", autoComplete: "off" },
  { name: "last_name", label: "Apellido", type: "text", autoComplete: "off" },
  {
    name: "national_id",
    label: "Cédula de identidad",
    type: "text",
    placeholder: "V-12345678",
    autoComplete: "off",
  },
  {
    name: "phone",
    label: "Teléfono",
    type: "tel",
    placeholder: "4141234567",
    autoComplete: "off",
  },
  { name: "email", label: "Correo", type: "email", autoComplete: "off" },
];

export function PatientFields({
  value,
  errors,
  onChange,
}: {
  value: PatientForm;
  errors: PatientErrors;
  onChange: (value: PatientForm) => void;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {FIELDS.map((f) => (
        <Field
          key={f.name}
          label={f.label}
          htmlFor={`patient-${f.name}`}
          required
          error={errors[f.name]}
        >
          <input
            id={`patient-${f.name}`}
            type={f.type}
            placeholder={f.placeholder}
            autoComplete={f.autoComplete}
            aria-invalid={Boolean(errors[f.name])}
            value={value[f.name]}
            onChange={(e) => onChange({ ...value, [f.name]: e.target.value })}
            className={clsx(fieldClass, errors[f.name] && invalidFieldClass)}
          />
        </Field>
      ))}
    </div>
  );
}
