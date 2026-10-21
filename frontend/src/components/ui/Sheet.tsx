import { useEffect, useRef, type ReactNode } from "react";

/** Diálogo modal nativo (<dialog>) con foco y Escape gestionados por el navegador. */
export function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
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
      className="m-auto w-[min(28rem,calc(100vw-2rem))] rounded-card border border-line bg-surface p-0 text-ink shadow-pop backdrop:bg-black/40"
    >
      {open && (
        <div className="p-5">
          <h2 className="mb-4 text-base font-semibold">{title}</h2>
          {children}
        </div>
      )}
    </dialog>
  );
}
