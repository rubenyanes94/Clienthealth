import clsx from "clsx";
import { Bell, ClipboardList } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useNotificationActions, useNotifications } from "@/api/hooks";
import type { AppNotification } from "@/api/types";
import { timeAgo } from "@/lib/format";
import { useNow } from "@/lib/useNow";
import { TASK_ICON } from "../cases/tasks";
import { notificationText } from "./text";

function Item({ n, onOpen }: { n: AppNotification; onOpen: (n: AppNotification) => void }) {
  const now = useNow(30_000);
  const { title, body } = notificationText(n);
  const Icon = n.task_type ? TASK_ICON[n.task_type] : ClipboardList;
  const unread = n.read_at === null;
  return (
    <li>
      <button
        type="button"
        onClick={() => onOpen(n)}
        className={clsx(
          "flex w-full items-start gap-3 border-b border-line px-4 py-3.5 text-left transition last:border-0 active:bg-surface-3",
          unread ? "bg-surface-2 hover:bg-surface-3" : "hover:bg-surface-2",
        )}
      >
        <span
          className={clsx(
            "flex size-10 shrink-0 items-center justify-center rounded-full",
            unread ? "bg-ink text-white" : "bg-surface-3 text-ink-3",
          )}
        >
          <Icon className="size-4" aria-hidden />
        </span>
        <span className="min-w-0 flex-1">
          <span className={clsx("block text-sm", unread ? "font-semibold" : "font-medium")}>
            {title}
          </span>
          <span className="mt-0.5 block text-sm leading-snug break-words text-ink-2">{body}</span>
          <span className="mt-1 flex items-center gap-1.5 text-xs text-ink-3">
            {timeAgo(n.created_at, now)}
            {unread && <span className="size-2 rounded-full bg-ink" aria-label="Sin leer" />}
          </span>
        </span>
      </button>
    </li>
  );
}

/**
 * Campana con su panel, en el encabezado de cada pantalla, antes del botón de acción. El panel se
 * abre en la misma pantalla, sin cambiar de página. Un círculo rojo avisa que hay algo sin leer.
 */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [place, setPlace] = useState<{ top: number; left: number; width: number; max: number }>();
  const box = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const navigate = useNavigate();
  const query = useNotifications();
  const { read, readAll } = useNotificationActions();
  const unread = query.data?.unread ?? 0;

  /** El encabezado recorta lo que se salga de él, así que el panel va fijo junto a la campana. */
  const toggle = () => {
    if (!open && button.current) {
      const rect = button.current.getBoundingClientRect();
      const width = Math.min(416, window.innerWidth - 16);
      const top = rect.bottom + 8;
      setPlace({
        top,
        width,
        left: Math.min(Math.max(8, rect.right - width), window.innerWidth - width - 8),
        max: Math.min(576, window.innerHeight - top - 12),
      });
    }
    setOpen((v) => !v);
  };

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    const onDown = (e: PointerEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) close();
    };
    // La página se desplaza por debajo; la lista del panel, no.
    const onScroll = (e: Event) => {
      if (!box.current?.contains(e.target as Node)) close();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", close);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", close);
    };
  }, [open]);

  const openItem = (n: AppNotification) => {
    if (n.read_at === null) read.mutate(n.id);
    setOpen(false);
    navigate(`/casos/${n.case.id}`);
  };

  return (
    <div ref={box} className="relative shrink-0">
      <button
        ref={button}
        type="button"
        aria-label={unread > 0 ? `Notificaciones (${unread} sin leer)` : "Notificaciones"}
        aria-expanded={open}
        onClick={toggle}
        className={clsx(
          "relative flex size-12 items-center justify-center rounded-full ring-1 ring-line transition active:scale-[0.97]",
          open ? "bg-ink text-white" : "bg-surface text-ink-2 shadow-xs hover:bg-surface-3",
        )}
      >
        <Bell className="size-5" aria-hidden />
        {unread > 0 && (
          <span
            aria-hidden
            className="absolute top-2.5 right-3 size-3 rounded-full bg-danger ring-2 ring-white"
          />
        )}
      </button>

      {open && place && (
        <section
          aria-label="Notificaciones"
          style={{ top: place.top, left: place.left, width: place.width, maxHeight: place.max }}
          className="fixed z-50 flex flex-col overflow-hidden rounded-3xl bg-surface text-ink shadow-pop"
        >
          <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">Notificaciones</h2>
            {unread > 0 && (
              <button
                type="button"
                onClick={() => readAll.mutate()}
                className="h-11 rounded-full px-4 text-sm font-medium text-ink-2 transition hover:bg-surface-3 hover:text-ink"
              >
                Marcar todas como leídas
              </button>
            )}
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {query.data?.items.length === 0 && (
              <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
                <span className="flex size-12 items-center justify-center rounded-full bg-surface-3">
                  <Bell className="size-5 text-ink-2" aria-hidden />
                </span>
                <p className="text-sm text-ink-3">
                  Aquí verá las tareas y los casos que le asignen.
                </p>
              </div>
            )}
            {query.error && <p className="p-4 text-sm text-danger">{query.error.message}</p>}
            <ul>
              {query.data?.items.map((n) => (
                <Item key={n.id} n={n} onOpen={openItem} />
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  );
}
