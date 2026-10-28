import { Sparkles } from "lucide-react";
import { useState } from "react";
import { useCatalog, useConversationActions, useCopilot } from "@/api/hooks";
import type { ConversationDetail } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { fieldClass, Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";

const SKIP_TEXT: Record<string, string> = {
  urgent: "No se enviará: no se pide calificación tras una urgencia.",
  cooldown: "No se enviará: el paciente ya recibió una encuesta hace poco.",
};

export function TransferDialog({
  conversation,
  open,
  onClose,
}: {
  conversation: ConversationDetail;
  open: boolean;
  onClose: () => void;
}) {
  const catalog = useCatalog();
  const { transfer } = useConversationActions(conversation.id);
  const toast = useToast();
  const [areaId, setAreaId] = useState<number | "">("");
  const areas = catalog.data?.areas.filter((a) => a.id !== conversation.area?.id) ?? [];

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Transferir a otra área"
      description="El caso vuelve a la cola del área elegida y deja de estar asignado a usted."
    >
      <label className="mb-1.5 block text-sm font-medium" htmlFor="transfer-area">
        Área
      </label>
      <select
        id="transfer-area"
        className={fieldClass}
        value={areaId}
        onChange={(e) => setAreaId(e.target.value ? Number(e.target.value) : "")}
      >
        <option value="">Seleccione…</option>
        {areas.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <div className="mt-7 grid grid-cols-2 gap-2.5">
        <Button size="lg" onClick={onClose}>
          Cancelar
        </Button>
        <Button
          size="lg"
          variant="primary"
          disabled={!areaId || transfer.isPending}
          onClick={() =>
            areaId &&
            transfer.mutate(areaId, {
              onSuccess: () => {
                toast.ok("Caso transferido");
                onClose();
              },
              onError: (e) => toast.error(e.message),
            })
          }
        >
          Transferir
        </Button>
      </div>
    </Sheet>
  );
}

export function CloseDialog({
  conversation,
  open,
  onClose,
}: {
  conversation: ConversationDetail;
  open: boolean;
  onClose: () => void;
}) {
  const catalog = useCatalog();
  const { close } = useConversationActions(conversation.id);
  const copilot = useCopilot(conversation.id);
  const toast = useToast();
  const [reasonId, setReasonId] = useState<number | "">("");
  const [sendSurvey, setSendSurvey] = useState(true);
  const skip = conversation.csat_skip_reason ?? null;
  const reasons =
    catalog.data?.reasons.filter(
      (r) => r.area_id === null || r.area_id === conversation.area?.id,
    ) ?? [];

  const suggestReason = () =>
    copilot.reason.mutate(undefined, {
      onSuccess: ({ reason }) => {
        if (reason) setReasonId(reason.id);
        else toast.error("El copiloto no encontró un motivo adecuado");
      },
      onError: (e) => toast.error(e.message),
    });

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Cerrar caso"
      description="El motivo es obligatorio: alimenta los indicadores."
    >
      <div className="mb-1.5 flex items-center justify-between">
        <label className="text-sm font-medium" htmlFor="close-reason">
          Motivo de contacto <span className="text-danger">*</span>
        </label>
        <Button variant="ai" size="sm" onClick={suggestReason} disabled={copilot.reason.isPending}>
          <Sparkles className="size-3.5" aria-hidden />
          {copilot.reason.isPending ? "Buscando…" : "Sugerir"}
        </Button>
      </div>
      <select
        id="close-reason"
        className={fieldClass}
        value={reasonId}
        onChange={(e) => setReasonId(e.target.value ? Number(e.target.value) : "")}
      >
        <option value="">Seleccione el motivo…</option>
        {reasons.map((r) => (
          <option key={r.id} value={r.id}>
            {r.name}
          </option>
        ))}
      </select>

      <label
        className={`mt-5 flex items-start gap-3 rounded-3xl p-4 ring-1 ring-inset ring-line ${skip ? "opacity-60" : "cursor-pointer hover:bg-surface-2"}`}
      >
        <input
          type="checkbox"
          className="mt-0.5 size-5 shrink-0 accent-ink"
          checked={sendSurvey && !skip}
          disabled={Boolean(skip)}
          onChange={(e) => setSendSurvey(e.target.checked)}
        />
        <span>
          <span className="block text-sm font-medium">Enviar encuesta de satisfacción</span>
          <span className="block text-xs text-ink-3">
            {skip
              ? (SKIP_TEXT[skip] ?? "No se enviará.")
              : "Plantilla de WhatsApp: el paciente califica la atención del 1 al 5."}
          </span>
        </span>
      </label>

      <div className="mt-7 grid grid-cols-2 gap-2.5">
        <Button size="lg" onClick={onClose}>
          Cancelar
        </Button>
        <Button
          size="lg"
          variant="primary"
          disabled={!reasonId || close.isPending}
          onClick={() =>
            reasonId &&
            close.mutate(
              { contact_reason_id: reasonId, send_survey: sendSurvey && !skip },
              {
                onSuccess: (result) => {
                  toast.ok(
                    result.surveys.some((s) => s.status === "sent")
                      ? "Caso cerrado · encuesta enviada"
                      : "Caso cerrado",
                  );
                  onClose();
                },
                onError: (e) => toast.error(e.message),
              },
            )
          }
        >
          Cerrar caso
        </Button>
      </div>
    </Sheet>
  );
}
