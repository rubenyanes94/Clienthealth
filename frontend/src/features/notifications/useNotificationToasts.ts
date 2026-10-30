import { useEffect, useRef } from "react";
import { useNotifications } from "@/api/hooks";
import { useToast } from "@/components/ui/Toast";
import { notificationText } from "./text";

/** Avisa con un mensaje breve cuando llega algo nuevo, aunque el panel esté cerrado. */
export function useNotificationToasts(enabled: boolean) {
  const query = useNotifications(enabled);
  const toast = useToast();
  // El primer resultado solo fija el punto de partida: no se avisa de lo que ya estaba.
  const lastSeen = useRef<number | null>(null);

  useEffect(() => {
    const items = query.data?.items;
    if (!items) return;
    const newest = items.reduce((max, n) => Math.max(max, n.id), 0);
    if (lastSeen.current !== null) {
      const fresh = items.filter((n) => n.id > lastSeen.current! && n.read_at === null);
      if (fresh.length === 1) toast.ok(notificationText(fresh[0]!).title);
      else if (fresh.length > 1) toast.ok(`${fresh.length} notificaciones nuevas`);
    }
    lastSeen.current = Math.max(newest, lastSeen.current ?? 0);
  }, [query.data, toast]);
}
