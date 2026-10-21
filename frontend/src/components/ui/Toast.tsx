import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import clsx from "clsx";

type Toast = { id: number; message: string; tone: "ok" | "error" };
type ToastApi = { ok: (message: string) => void; error: (message: string) => void };

const ToastContext = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string, tone: Toast["tone"]) => {
    const id = Date.now() + Math.random();
    setToasts((all) => [...all, { id, message, tone }]);
    window.setTimeout(() => setToasts((all) => all.filter((t) => t.id !== id)), 4500);
  }, []);
  const [api] = useState<ToastApi>(() => ({
    ok: (m) => push(m, "ok"),
    error: (m) => push(m, "error"),
  }));

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-4 bottom-20 z-50 md:bottom-4 flex flex-col items-center gap-2 sm:inset-x-auto sm:right-4 sm:items-end"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className={clsx(
              "pointer-events-auto max-w-sm rounded-xl px-4 py-2.5 text-sm font-medium shadow-pop",
              toast.tone === "ok" ? "bg-ink text-white" : "bg-danger text-white",
            )}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast fuera de ToastProvider");
  return ctx;
}
