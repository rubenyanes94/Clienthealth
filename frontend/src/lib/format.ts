import type { ConversationStatus, EventType } from "@/api/types";

export const TIMEZONE = "America/Caracas";

const timeFmt = new Intl.DateTimeFormat("es-VE", {
  timeZone: TIMEZONE,
  hour: "numeric",
  minute: "2-digit",
});
const dateTimeFmt = new Intl.DateTimeFormat("es-VE", {
  timeZone: TIMEZONE,
  day: "2-digit",
  month: "short",
  hour: "numeric",
  minute: "2-digit",
});
const dayFmt = new Intl.DateTimeFormat("es-VE", { timeZone: TIMEZONE, dateStyle: "medium" });
const dayKeyFmt = new Intl.DateTimeFormat("en-CA", { timeZone: TIMEZONE });

export function formatTime(iso: string): string {
  return timeFmt.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTimeFmt.format(new Date(iso));
}

export function formatDay(iso: string): string {
  return dayFmt.format(new Date(iso));
}

/** Clave de día en la zona del centro, para agrupar mensajes. */
export function dayKey(iso: string): string {
  return dayKeyFmt.format(new Date(iso));
}

/** Hora si es de hoy; fecha corta si no. */
export function formatListTime(iso: string, now = new Date()): string {
  return dayKey(iso) === dayKey(now.toISOString()) ? formatTime(iso) : formatDay(iso);
}

export function formatElapsed(fromIso: string, now: number): string {
  const seconds = Math.max(0, Math.floor((now - new Date(fromIso).getTime()) / 1000));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h >= 24) return `${Math.floor(h / 24)} d ${h % 24} h`;
  if (h > 0) return `${h} h ${String(m).padStart(2, "0")} min`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** "hace 5 min", "hace 2 h"; pasado un día, la fecha. */
export function timeAgo(iso: string, now: number): string {
  const minutes = Math.floor((now - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "ahora";
  if (minutes < 60) return `hace ${minutes} min`;
  if (minutes < 24 * 60) return `hace ${Math.floor(minutes / 60)} h`;
  return formatDateTime(iso);
}

export function displayPhone(waId: string): string {
  // 58 414 123 4567
  const m = waId.match(/^(58)(\d{3})(\d{3})(\d{4})$/);
  return m ? `+${m[1]} ${m[2]} ${m[3]} ${m[4]}` : `+${waId}`;
}

/** Teléfono de un paciente: 4141234567. Un número extranjero conserva su código de país. */
export function patientPhone(phone: string): string {
  return /^58\d{10}$/.test(phone) ? phone.slice(2) : `+${phone}`;
}

export const STATUS_LABEL: Record<ConversationStatus, string> = {
  bot: "En el bot",
  queued: "En cola",
  open: "Abierta",
  pending: "En espera",
  closed: "Cerrada",
};

export const EVENT_LABEL: Record<EventType, string> = {
  created: "Conversación iniciada",
  inbound_message: "Mensaje del paciente",
  bot_message: "Respuesta automática",
  bot_escalated: "Derivada a un agente",
  bot_resolved: "Resuelta por el bot",
  urgency_detected: "Urgencia detectada",
  accepted: "Caso aceptado",
  agent_message: "Respuesta del agente",
  internal_note: "Nota interna",
  pending_started: "En espera del paciente",
  pending_resumed: "Reanudada",
  transferred: "Transferida de área",
  closed: "Caso cerrado",
  reopened: "Caso reabierto",
  abandoned: "Marcada como abandonada",
  survey_sent: "Encuesta enviada",
  survey_answered: "Encuesta respondida",
  case_created: "Caso creado desde el chat",
};
