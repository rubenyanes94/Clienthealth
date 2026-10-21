import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { useMe } from "@/api/hooks";

export function RequireAuth({ children }: { children: ReactNode }) {
  const me = useMe();
  const location = useLocation();
  if (me.isPending) {
    return <div className="flex min-h-dvh items-center justify-center text-ink-3">Cargando…</div>;
  }
  if (!me.data) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }
  return children;
}
