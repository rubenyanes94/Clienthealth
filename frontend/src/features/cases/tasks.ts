import { Mail, MessageCircle, Phone, type LucideIcon } from "lucide-react";
import type { CaseTaskType } from "@/api/types";

export const TASK_TYPES: CaseTaskType[] = ["call", "whatsapp", "email"];

export const TASK_LABEL: Record<CaseTaskType, string> = {
  call: "Llamar",
  whatsapp: "WhatsApp",
  email: "Correo",
};

export const TASK_ICON: Record<CaseTaskType, LucideIcon> = {
  call: Phone,
  whatsapp: MessageCircle,
  email: Mail,
};
