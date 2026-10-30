import clsx from "clsx";
import {
  BarChart3,
  ClipboardList,
  FileText,
  HeartPulse,
  LogOut,
  MessagesSquare,
  UserCog,
  Users,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { useCasesLive, useInboxChanges, useLiveMetrics, useLogout, useMe } from "@/api/hooks";
import { Avatar } from "@/components/ui/Avatar";
import { useNotificationToasts } from "./features/notifications/useNotificationToasts";
import { AccountDialog } from "./features/users/AccountDialog";

const NAV = [
  { to: "/casos", label: "Casos", icon: ClipboardList, roles: ["agent", "supervisor", "admin"] },
  {
    to: "/conversaciones",
    label: "Conversaciones",
    icon: MessagesSquare,
    roles: ["agent", "supervisor", "admin"],
  },
  { to: "/pacientes", label: "Pacientes", icon: Users, roles: ["agent", "supervisor", "admin"] },
  { to: "/paneles", label: "Paneles", icon: BarChart3, roles: ["supervisor", "admin"] },
  { to: "/informes", label: "Informes", icon: FileText, roles: ["supervisor", "admin"] },
  { to: "/usuarios", label: "Usuarios", icon: UserCog, roles: ["admin"] },
];

/**
 * Menú lateral negro y flotante (barra inferior en el teléfono). Iconos grandes con su etiqueta
 * debajo: se toca con el dedo en la tableta sin tener que adivinar qué es cada uno.
 */
export function AppShell() {
  const me = useMe();
  const live = useLiveMetrics();
  const room = useCasesLive();
  const logout = useLogout();
  const [account, setAccount] = useState(false);
  useInboxChanges(Boolean(me.data));
  useNotificationToasts(Boolean(me.data));

  return (
    <div className="flex h-dvh flex-col bg-canvas md:flex-row md:gap-3 md:p-3">
      <nav
        aria-label="Principal"
        className="order-last m-2 mt-0 flex shrink-0 rounded-3xl bg-ink p-1.5 text-white shadow-pop md:order-first md:m-0 md:w-24 md:flex-col md:items-center md:overflow-y-auto md:rounded-[2rem] md:px-0 md:py-4 md:[scrollbar-width:none]"
      >
        <div
          className="mb-4 hidden size-12 shrink-0 items-center justify-center rounded-full bg-white text-ink md:flex"
          title="Atención al Paciente · CM San Bernardino"
        >
          <HeartPulse className="size-5" aria-hidden />
        </div>
        <ul className="flex flex-1 justify-around md:flex-none md:flex-col md:gap-1">
          {NAV.filter((item) => me.data && item.roles.includes(me.data.role)).map(
            ({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  className="group flex flex-col items-center gap-1 rounded-full px-2 py-1 text-[11px] font-medium md:px-0 md:py-0"
                >
                  {({ isActive }) => (
                    <>
                      <span
                        className={clsx(
                          "relative flex size-11 items-center justify-center rounded-full transition md:size-12",
                          isActive
                            ? "bg-white text-ink shadow-card"
                            : "text-white/60 group-hover:bg-white/10 group-hover:text-white",
                        )}
                      >
                        <Icon className="size-5" aria-hidden />
                        {to === "/casos" && room.data && room.data.registered > 0 && (
                          <span
                            title="Casos por atender"
                            className={clsx(
                              "absolute -top-0.5 -right-0.5 min-w-5 rounded-full px-1 text-center text-[11px] leading-5 font-semibold tabular-nums ring-2 ring-ink",
                              room.data.late > 0 ? "bg-danger text-white" : "bg-white text-ink",
                            )}
                          >
                            {room.data.registered}
                          </span>
                        )}
                        {to === "/conversaciones" && live.data && live.data.queued > 0 && (
                          <span
                            title="Casos en cola"
                            className={clsx(
                              "absolute -top-0.5 -right-0.5 min-w-5 rounded-full px-1 text-center text-[11px] leading-5 font-semibold tabular-nums ring-2 ring-ink",
                              live.data.urgent_queued > 0
                                ? "bg-danger text-white"
                                : "bg-white text-ink",
                            )}
                          >
                            {live.data.queued}
                          </span>
                        )}
                      </span>
                      <span
                        className={clsx(
                          "max-w-22 truncate text-[10px] md:text-[11px]",
                          isActive ? "text-white" : "text-white/50 group-hover:text-white",
                        )}
                      >
                        {label}
                      </span>
                    </>
                  )}
                </NavLink>
              </li>
            ),
          )}
        </ul>
        {live.data && (
          <dl className="mt-4 hidden w-16 space-y-2 rounded-2xl bg-white/10 px-1 py-3 text-center [@media(min-height:60rem)]:md:block">
            {(
              [
                ["En cola", live.data.queued],
                ["Abiertas", live.data.open],
                ["Agentes", live.data.agents_online],
              ] as const
            ).map(([label, value]) => (
              <div key={label}>
                <dd className="text-lg leading-none font-semibold tabular-nums">{value}</dd>
                <dt className="mt-0.5 text-[10px] text-white/50">{label}</dt>
              </div>
            ))}
          </dl>
        )}

        {/* El nombre siempre a la vista: en una tableta compartida, se ve con qué cuenta se trabaja. */}
        <div className="mt-auto hidden flex-col items-center gap-1 pt-4 md:flex">
          <button
            type="button"
            onClick={() => setAccount(true)}
            aria-label="Mi cuenta"
            className="flex w-full flex-col items-center gap-1 rounded-2xl py-1 transition hover:bg-white/10"
          >
            <Avatar name={me.data?.name} size="sm" />
            <span className="max-w-22 truncate text-[11px] font-medium text-white">
              {me.data?.name.split(" ")[0]}
            </span>
          </button>
          <button
            type="button"
            onClick={() => logout.mutate()}
            aria-label="Salir"
            title="Salir"
            className="flex size-11 items-center justify-center rounded-full text-white/60 transition hover:bg-white/10 hover:text-white"
          >
            <LogOut className="size-5" aria-hidden />
          </button>
        </div>
      </nav>
      <main className="min-h-0 min-w-0 flex-1">
        <Outlet />
      </main>
      <AccountDialog open={account} onClose={() => setAccount(false)} />
    </div>
  );
}
