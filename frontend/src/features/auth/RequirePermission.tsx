import { Lock } from "lucide-react";
import type { ReactNode } from "react";
import { useMe } from "@/api/hooks";
import type { Permission } from "@/api/types";
import { useCan } from "./permissions";

/** Muestra la pantalla solo con el permiso; si no, explica por qué no está disponible. */
export function RequirePermission({
  permission,
  message,
  children,
}: {
  permission: Permission;
  message: string;
  children: ReactNode;
}) {
  const me = useMe();
  const can = useCan();
  if (!me.data) return null;
  if (!can(permission)) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-4 text-center">
        <div className="flex size-14 items-center justify-center rounded-full bg-ink text-white">
          <Lock className="size-5" aria-hidden />
        </div>
        <p className="max-w-sm text-sm text-ink-3">{message}</p>
      </div>
    );
  }
  return children;
}
