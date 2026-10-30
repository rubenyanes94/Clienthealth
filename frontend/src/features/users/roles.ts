import type { AgentRole } from "@/api/types";

export const ROLE_LABEL: Record<AgentRole, string> = {
  agent: "Agente",
  supervisor: "Supervisor",
  admin: "Administrador",
};

export const ROLES: AgentRole[] = ["agent", "supervisor", "admin"];

export const MIN_PASSWORD = 10;
