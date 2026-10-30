import type { PatientIn } from "@/api/types";

export type PatientForm = PatientIn;
export type PatientErrors = Partial<Record<keyof PatientForm, string>>;

export const EMPTY_PATIENT: PatientForm = {
  first_name: "",
  last_name: "",
  national_id: "",
  phone: "",
  email: "",
};

/** 4141234567, también con 0 o +58 delante; o un número extranjero con su código de país. */
function isValidPhone(phone: string): boolean {
  const digits = phone.replace(/\D/g, "");
  return (
    /^0?[1-9]\d{9}$/.test(digits) ||
    /^58[1-9]\d{9}$/.test(digits) ||
    (/^[1-9]\d{10,14}$/.test(digits) && !digits.startsWith("58"))
  );
}

/** El backend vuelve a validar y normaliza: aquí solo se avisa antes de enviar. */
export function validatePatient(form: PatientForm): PatientErrors {
  const errors: PatientErrors = {};
  const required = "Complete este campo";
  if (form.first_name.trim().length < 2) errors.first_name = required;
  if (form.last_name.trim().length < 2) errors.last_name = required;
  if (!form.national_id.trim()) errors.national_id = required;
  else if (form.national_id.replace(/[\s.-]/g, "").length < 5)
    errors.national_id = "Cédula no válida";
  if (!form.phone.trim()) errors.phone = required;
  else if (!isValidPhone(form.phone)) errors.phone = "Escríbalo así: 4141234567";
  if (!form.email.trim()) errors.email = required;
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) errors.email = "Correo no válido";
  return errors;
}

/** Propuesta a partir del nombre de perfil de WhatsApp; el agente la corrige si hace falta. */
export function splitName(name: string | null | undefined): {
  first_name: string;
  last_name: string;
} {
  const words = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (words.length < 2) return { first_name: words[0] ?? "", last_name: "" };
  const cut = words.length >= 4 ? 2 : 1;
  return { first_name: words.slice(0, cut).join(" "), last_name: words.slice(cut).join(" ") };
}
