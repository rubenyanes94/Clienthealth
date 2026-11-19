import { useMe } from "@/api/hooks";
import type { Permission } from "@/api/types";

/** Qué permite cada permiso, en palabras del personal (Mi cuenta y el manual). */
export const PERMISSION_LABEL: Record<Permission, string> = {
  "cases.manage": "Crear casos y gestionarlos: etapas, asignar, transferir, editar y notas",
  "cases.history": "Ver la historia de los casos, incluido el chat del que nacieron",
  "tasks.assign": "Asignar tareas a cualquier persona y completarlas",
  "patients.manage": "Registrar, buscar y editar pacientes",
  "conversations.area": "Atender los chats de WhatsApp de su área",
  "conversations.all": "Ver todos los chats, incluidos los del bot",
  "simulator.use": "Simular mensajes de prueba (fuera de producción)",
  "directory.view": "Consultar el directorio de médicos y consultorios",
  "directory.manage": "Actualizar el directorio desde la web del centro",
  "metrics.view": "Ver Paneles e Informes",
  "users.manage": "Crear y gestionar cuentas de usuario",
  "catalog.manage": "Configurar áreas, motivos, preguntas del bot y horarios",
};

/**
 * Lo que la sesión permite, según la matriz del servidor (`app/core/permissions.py`).
 * Ocultar algo aquí es comodidad: quien decide es siempre el servidor.
 */
export function useCan(): (permission: Permission) => boolean {
  const me = useMe();
  const granted = me.data?.permissions ?? [];
  return (permission) => granted.includes(permission);
}
