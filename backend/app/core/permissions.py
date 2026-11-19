"""Permisología: qué puede hacer cada rol. Es la única fuente de verdad.

El servidor la aplica en cada ruta (`require_permission`) y la interfaz la recibe en `/auth/me`
para mostrar solo lo que cada persona puede usar. Para cambiar lo que hace un rol, se cambia aquí.
"""

from enum import StrEnum

from app.models.enums import AgentRole


class Permission(StrEnum):
    # Módulo de Casos: todas las áreas ven y gestionan todos los casos (decisión del producto).
    CASES_MANAGE = "cases.manage"  # crear, cambiar etapa, tomar, asignar, transferir, editar, notas
    CASES_HISTORY = "cases.history"  # actividad, notas, tareas y el chat del que nació el caso
    TASKS_ASSIGN = "tasks.assign"  # asignar tareas a cualquier persona, completarlas y cancelarlas
    PATIENTS_MANAGE = "patients.manage"  # registrar, buscar y editar pacientes
    # Conversaciones de WhatsApp.
    CONVERSATIONS_AREA = "conversations.area"  # la cola de su área y sus propios chats
    CONVERSATIONS_ALL = "conversations.all"  # todos los chats, incluidos los del bot
    SIMULATOR_USE = "simulator.use"  # inyectar mensajes de prueba (nunca en producción)
    # Directorio de médicos y consultorios (información pública de la web del centro).
    DIRECTORY_VIEW = "directory.view"
    DIRECTORY_MANAGE = "directory.manage"  # actualizarlo desde la web
    # Gestión.
    METRICS_VIEW = "metrics.view"  # Paneles e Informes
    USERS_MANAGE = "users.manage"  # crear, editar y desactivar cuentas
    CATALOG_MANAGE = "catalog.manage"  # áreas, motivos, preguntas del bot y calendario


EMPLOYEE = frozenset(
    {
        Permission.CASES_MANAGE,
        Permission.CASES_HISTORY,
        Permission.TASKS_ASSIGN,
        Permission.PATIENTS_MANAGE,
        Permission.CONVERSATIONS_AREA,
        Permission.DIRECTORY_VIEW,
    }
)

ROLE_PERMISSIONS: dict[AgentRole, frozenset[Permission]] = {
    AgentRole.AGENT: EMPLOYEE,
    AgentRole.SUPERVISOR: EMPLOYEE
    | {Permission.CONVERSATIONS_ALL, Permission.SIMULATOR_USE, Permission.METRICS_VIEW},
    AgentRole.ADMIN: frozenset(Permission),
}


def permissions_of(role: AgentRole) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def has(role: AgentRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
