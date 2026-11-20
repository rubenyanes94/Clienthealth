import { Copy, Download, Globe, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { useDirectoryImport } from "@/api/hooks";
import type { DirectoryImportPreview, WpExport } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";
import {
  EXPORT_SCRIPT,
  fetchFromWebsite,
  parseExportFile,
  SOURCE_SITE,
  WebsiteUnreachable,
} from "./source";

function Summary({ preview }: { preview: DirectoryImportPreview }) {
  const items: [string, number][] = [
    ["Nuevos", preview.created],
    ["Con cambios", preview.updated],
    ["Sin cambios", preview.unchanged],
    ["Ya no están en la web", preview.removed],
  ];
  return (
    <>
      <dl className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {items.map(([label, value]) => (
          <div key={label} className="rounded-2xl bg-surface-2 px-4 py-3">
            <dt className="text-xs text-ink-3">{label}</dt>
            <dd className="mt-1 text-2xl font-bold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-sm text-ink-3">
        {preview.total} médicos en la web.
        {preview.skipped_posts > 0 &&
          ` Se ignoraron ${preview.skipped_posts} entradas que no son fichas de médicos.`}
      </p>
      {preview.removed_names.length > 0 && (
        <div className="mt-4">
          <h3 className="mb-1 text-sm font-semibold">Se retirarán del directorio</h3>
          <p className="text-sm text-ink-2">{preview.removed_names.join(" · ")}</p>
        </div>
      )}
      {preview.needs_review.length > 0 && (
        <div className="mt-4">
          <h3 className="mb-1 text-sm font-semibold">
            Para revisar ({preview.needs_review.length})
          </h3>
          <p className="mb-2 text-xs text-ink-3">
            Se importan igual; su ficha mostrará el texto original de la web.
          </p>
          <ul className="max-h-48 space-y-2 overflow-y-auto rounded-2xl bg-warn-soft p-3 text-sm">
            {preview.needs_review.map((r) => (
              <li key={r.name}>
                <span className="font-medium">{r.name}</span>
                <span className="text-warn"> — {r.notes.join(" · ")}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

function ImportFlow({ onClose }: { onClose: () => void }) {
  const run = useDirectoryImport();
  const toast = useToast();
  const file = useRef<HTMLInputElement>(null);
  const [data, setData] = useState<WpExport | null>(null);
  const [preview, setPreview] = useState<DirectoryImportPreview | null>(null);
  const [reading, setReading] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showScript, setShowScript] = useState(false);
  const [copied, setCopied] = useState(false);

  const check = (body: WpExport) => {
    setData(body);
    setError(null);
    run.mutate(
      { body, apply: false },
      { onSuccess: setPreview, onError: (e) => setError(e.message) },
    );
  };

  const fromWeb = async () => {
    setError(null);
    setReading(0);
    try {
      check(await fetchFromWebsite(setReading));
    } catch (e) {
      if (e instanceof WebsiteUnreachable) setShowScript(true);
      setError((e as Error).message);
    } finally {
      setReading(null);
    }
  };

  const fromFile = async (picked: File | undefined) => {
    if (!picked) return;
    try {
      check(parseExportFile(await picked.text()));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (preview && data) {
    return (
      <>
        <Summary preview={preview} />
        {error && (
          <p role="alert" className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
            {error}
          </p>
        )}
        <div className="mt-7 grid grid-cols-2 gap-2.5">
          <Button size="lg" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            size="lg"
            variant="primary"
            disabled={run.isPending}
            onClick={() =>
              run.mutate(
                { body: data, apply: true },
                {
                  onSuccess: (r) => {
                    toast.ok(`Directorio actualizado: ${r.total} médicos`);
                    onClose();
                  },
                  onError: (e) => setError(e.message),
                },
              )
            }
          >
            {run.isPending ? "Guardando…" : "Aplicar cambios"}
          </Button>
        </div>
      </>
    );
  }

  const busy = reading !== null || run.isPending;
  return (
    <>
      <div className="grid gap-2.5 sm:grid-cols-2">
        <Button size="lg" variant="primary" disabled={busy} onClick={fromWeb}>
          <Globe className="size-5" aria-hidden />
          {reading !== null
            ? `Leyendo la web… ${reading} fichas`
            : run.isPending
              ? "Analizando…"
              : "Traer desde la web"}
        </Button>
        <Button size="lg" disabled={busy} onClick={() => file.current?.click()}>
          <Upload className="size-5" aria-hidden /> Importar archivo
        </Button>
        <input
          ref={file}
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={(e) => void fromFile(e.target.files?.[0])}
        />
      </div>
      <p className="mt-3 text-sm text-ink-3">
        Se lee desde este navegador, porque la web del centro solo responde desde Venezuela. Antes
        de guardar verá qué cambia.
      </p>
      {error && (
        <p role="alert" className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {error}
        </p>
      )}

      <div className="mt-6 rounded-3xl bg-surface-2 p-4">
        <button
          type="button"
          onClick={() => setShowScript((v) => !v)}
          className="flex w-full items-center justify-between text-left text-sm font-semibold"
          aria-expanded={showScript}
        >
          Plan B: descargar el archivo desde la web
          <span className="text-ink-3">{showScript ? "−" : "+"}</span>
        </button>
        {showScript && (
          <div className="mt-3 text-sm text-ink-2">
            <ol className="list-decimal space-y-1 pl-5">
              <li>
                Abra{" "}
                <a href={SOURCE_SITE} target="_blank" rel="noreferrer" className="underline">
                  la web del centro
                </a>{" "}
                en otra pestaña.
              </li>
              <li>Pulse F12 y vaya a la pestaña «Consola».</li>
              <li>
                Pegue el script y pulse Enter. Si el navegador lo pide, escriba primero «allow
                pasting».
              </li>
              <li>Se descargará «directorio.json»: impórtelo con el botón de arriba.</li>
            </ol>
            <Button
              className="mt-3"
              onClick={() => {
                void navigator.clipboard?.writeText(EXPORT_SCRIPT).then(() => setCopied(true));
              }}
            >
              {copied ? (
                <Download className="size-4" aria-hidden />
              ) : (
                <Copy className="size-4" aria-hidden />
              )}
              {copied ? "Script copiado" : "Copiar el script"}
            </Button>
          </div>
        )}
      </div>
    </>
  );
}

export function ImportDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Sheet
      open={open}
      onClose={onClose}
      size="lg"
      title="Actualizar el directorio"
      description="Trae las fichas de los médicos desde la web del centro."
    >
      <ImportFlow onClose={onClose} />
    </Sheet>
  );
}
