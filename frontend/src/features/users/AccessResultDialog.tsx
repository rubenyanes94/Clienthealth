import { Copy } from "lucide-react";
import { useState } from "react";
import type { Access } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Sheet } from "@/components/ui/Sheet";

/**
 * Lo que pasó con el correo cuando no se pudo enviar: el error, o en pruebas (sin servidor de
 * correo) el enlace para compartirlo a mano. Si se envió, basta un aviso breve y no se abre.
 */
export function AccessResultDialog({
  result,
  email,
  onRetry,
  onClose,
}: {
  result: Access | null;
  email: string;
  onRetry: () => void;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const open = result !== null && !result.email_sent;
  const link = result?.link_path ? window.location.origin + result.link_path : null;

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={link ? "Modo pruebas: el correo no se envió" : "No se pudo enviar el correo"}
      description={
        link
          ? "No hay servidor de correo configurado. Comparta este enlace con la persona; en producción le llegará por correo."
          : `La cuenta de ${email} está creada, pero el correo no salió.`
      }
    >
      {link ? (
        <>
          <p className="rounded-2xl bg-surface-2 px-4 py-3 font-mono text-xs break-all text-ink-2">
            {link}
          </p>
          <div className="mt-6 grid grid-cols-2 gap-2.5">
            <Button size="lg" onClick={onClose}>
              Cerrar
            </Button>
            <Button
              size="lg"
              variant="primary"
              onClick={() => {
                void navigator.clipboard?.writeText(link).then(() => setCopied(true));
              }}
            >
              <Copy className="size-4" aria-hidden /> {copied ? "Copiado" : "Copiar enlace"}
            </Button>
          </div>
        </>
      ) : (
        <>
          <p className="rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
            {result?.error ?? "Error desconocido"}
          </p>
          <div className="mt-6 grid grid-cols-2 gap-2.5">
            <Button size="lg" onClick={onClose}>
              Cerrar
            </Button>
            <Button size="lg" variant="primary" onClick={onRetry}>
              Reintentar
            </Button>
          </div>
        </>
      )}
    </Sheet>
  );
}
