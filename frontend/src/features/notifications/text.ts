import type { AppNotification, CaseTaskType } from "@/api/types";
import { TASK_LABEL } from "../cases/tasks";

const TASK_VERB: Record<CaseTaskType, string> = {
  call: "llamar a",
  whatsapp: "escribir por WhatsApp a",
  email: "enviar un correo a",
};

/** El texto se arma al mostrarlo: la notificación solo apunta al caso y a la tarea. */
export function notificationText(n: AppNotification): { title: string; body: string } {
  const who = n.actor?.name ?? "Alguien";
  if (n.type === "task_assigned" && n.task_type) {
    return {
      title: `Nueva tarea: ${TASK_LABEL[n.task_type]}`,
      body: `${who} le asignó ${TASK_VERB[n.task_type]} ${n.case.patient_name} · Caso #${n.case.id}`,
    };
  }
  return {
    title: "Caso asignado",
    body: `${who} le asignó el caso #${n.case.id} «${n.case.subject}» de ${n.case.patient_name}`,
  };
}
