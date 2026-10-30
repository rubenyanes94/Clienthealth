import { X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

/** Diálogo modal nativo (<dialog>) con foco y Escape gestionados por el navegador. */
export function Sheet({
  open,
  onClose,
  title,
  description,
  size = "md",
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  size?: "md" | "lg";
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal?.();
    if (!open && dialog.open) dialog.close?.();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-label={title}
      className={`m-auto ${size === "lg" ? "w-[min(56rem,calc(100vw-2rem))]" : "w-[min(32rem,calc(100vw-2rem))]"} rounded-3xl bg-surface p-0 text-ink shadow-pop backdrop:bg-zinc-950/40 backdrop:backdrop-blur-[3px]`}
    >
      {open && (
        <div className="p-7">
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">{title}</h2>
              {description && <p className="mt-1 text-sm text-ink-3">{description}</p>}
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar"
              className="-m-1 flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-3 text-ink-2 transition hover:bg-line-strong hover:text-ink"
            >
              <X className="size-4" />
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}

export const fieldClass =
  "h-12 w-full rounded-2xl bg-surface-2 px-4 text-base ring-1 ring-inset ring-line-strong outline-none transition placeholder:text-ink-3 focus:bg-surface focus:ring-2 focus:ring-ink";
