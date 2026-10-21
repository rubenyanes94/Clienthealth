import clsx from "clsx";
import {
  BarChart3,
  ClipboardList,
  FileText,
  HeartPulse,
  LogOut,
  MessagesSquare,
  Users,
} from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { useInboxChanges, useLiveMetrics, useLogout, useMe } from "@/api/hooks";
import { Avatar } from "@/components/ui/Avatar";

const NAV = [
  { to: "/conversaciones", label: "Conversaciones", icon: MessagesSquare },
  { to: "/casos", label: "Casos", icon: ClipboardList },
  { to: "/paneles", label: "Paneles", icon: BarChart3 },
  { to: "/informes", label: "Informes", icon: FileText },
  { to: "/contactos", label: "Contactos", icon: Users },
];

const ROLE_LABEL: Record<string, string> = {
  agent: "Agente",
  supervisor: "Supervisor",
  admin: "Administrador",
};

export function AppShell() {
  const me = useMe();
  const live = useLiveMetrics();
  const logout = useLogout();
  useInboxChanges(Boolean(me.data));

  return (
    <div className="flex h-dvh flex-col bg-canvas md:flex-row">
      <nav
        aria-label="Principal"
        className="order-last flex shrink-0 border-t border-line bg-surface md:order-first md:w-60 md:flex-col md:border-t-0 md:border-r"
      >
        <div className="hidden items-center gap-3 px-5 pt-5 pb-6 md:flex">
          <div className="flex size-9 items-center justify-center rounded-xl bg-ink text-white shadow-card">
            <HeartPulse className="size-[18px]" aria-hidden />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight">Atención al Paciente</div>
            <div className="text-xs text-ink-3">CM San Bernardino</div>
          </div>
        </div>
        <ul className="flex flex-1 justify-around md:flex-none md:flex-col md:gap-0.5 md:px-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  clsx(
                    "group flex flex-col items-center gap-0.5 px-3 py-2 text-[11px] font-medium transition md:flex-row md:gap-3 md:rounded-lg md:text-sm",
                    isActive
                      ? "text-ink md:bg-surface-3"
                      : "text-ink-3 hover:text-ink md:hover:bg-surface-2",
                  )
                }
              >
                <Icon className="size-5 md:size-4" aria-hidden />
                <span>{label}</span>
                {to === "/conversaciones" && live.data && live.data.queued > 0 && (
                  <span
                    title="Casos en cola"
                    className={clsx(
                      "ml-auto hidden min-w-5 rounded-full px-1.5 text-center text-[11px] leading-5 font-semibold tabular-nums md:inline",
                      live.data.urgent_queued > 0 ? "bg-danger text-white" : "bg-ink text-white",
                    )}
                  >
                    {live.data.queued}
                  </span>
                )}
              </NavLink>
            </li>
          ))}
        </ul>

        {live.data && (
          <div className="mx-3 mt-6 hidden rounded-xl border border-line p-3 md:block">
            <div className="mb-2 text-[11px] font-medium tracking-wide text-ink-3 uppercase">
              Ahora
            </div>
            <dl className="grid grid-cols-2 gap-y-1.5 text-sm">
              <dt className="text-ink-3">En cola</dt>
              <dd className="text-right font-semibold tabular-nums">{live.data.queued}</dd>
              <dt className="text-ink-3">Abiertas</dt>
              <dd className="text-right font-semibold tabular-nums">{live.data.open}</dd>
              <dt className="text-ink-3">Agentes</dt>
              <dd className="text-right font-semibold tabular-nums">{live.data.agents_online}</dd>
            </dl>
          </div>
        )}

        <div className="mt-auto hidden items-center gap-3 border-t border-line p-4 md:flex">
          <Avatar name={me.data?.name} size="sm" />
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{me.data?.name}</div>
            <div className="text-xs text-ink-3">{ROLE_LABEL[me.data?.role ?? ""]}</div>
          </div>
          <button
            type="button"
            onClick={() => logout.mutate()}
            aria-label="Salir"
            title="Salir"
            className="rounded-lg p-1.5 text-ink-3 transition hover:bg-surface-3 hover:text-ink"
          >
            <LogOut className="size-4" aria-hidden />
          </button>
        </div>
      </nav>
      <main className="min-h-0 min-w-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}
