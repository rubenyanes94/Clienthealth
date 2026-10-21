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

const NAV = [
  { to: "/conversaciones", label: "Conversaciones", icon: MessagesSquare },
  { to: "/casos", label: "Casos", icon: ClipboardList },
  { to: "/paneles", label: "Paneles", icon: BarChart3 },
  { to: "/informes", label: "Informes", icon: FileText },
  { to: "/contactos", label: "Contactos", icon: Users },
];

export function AppShell() {
  const me = useMe();
  const live = useLiveMetrics();
  const logout = useLogout();
  useInboxChanges(Boolean(me.data));

  return (
    <div className="flex h-dvh flex-col md:flex-row">
      <nav
        aria-label="Principal"
        className="order-last flex shrink-0 border-t border-line bg-surface md:order-first md:w-56 md:flex-col md:border-t-0 md:border-r"
      >
        <div className="hidden items-center gap-2.5 px-4 py-4 md:flex">
          <div className="flex size-8 items-center justify-center rounded-lg bg-brand text-brand-ink">
            <HeartPulse className="size-4" aria-hidden />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold">Atención</div>
            <div className="text-xs text-ink-3">CM San Bernardino</div>
          </div>
        </div>
        <ul className="flex flex-1 justify-around md:flex-none md:flex-col md:gap-0.5 md:px-2">
          {NAV.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  clsx(
                    "flex flex-col items-center gap-0.5 px-3 py-2 text-[11px] font-medium md:flex-row md:gap-2.5 md:rounded-lg md:text-sm",
                    isActive ? "text-brand md:bg-brand-soft" : "text-ink-2 hover:text-ink",
                  )
                }
              >
                <Icon className="size-5 md:size-4" aria-hidden />
                <span>{label}</span>
                {to === "/conversaciones" && live.data && live.data.queued > 0 && (
                  <span
                    title="Casos en cola"
                    className={clsx(
                      "ml-auto hidden rounded-full px-1.5 text-[11px] leading-5 md:inline",
                      live.data.urgent_queued > 0
                        ? "bg-danger text-white"
                        : "bg-surface-2 text-ink-2",
                    )}
                  >
                    {live.data.queued}
                  </span>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="mt-auto hidden border-t border-line p-3 md:block">
          <div className="truncate text-sm font-medium">{me.data?.name}</div>
          <div className="mb-2 text-xs text-ink-3 capitalize">{me.data?.role}</div>
          <button
            type="button"
            onClick={() => logout.mutate()}
            className="flex items-center gap-1.5 text-sm text-ink-2 hover:text-danger"
          >
            <LogOut className="size-4" aria-hidden /> Salir
          </button>
        </div>
      </nav>
      <main className="min-h-0 min-w-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}
