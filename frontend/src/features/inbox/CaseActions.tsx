import { useState } from "react";
import { useCatalog, useConversationActions } from "@/api/hooks";
import type { ConversationDetail } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";

const selectClass =
  "h-10 w-full rounded-lg border border-line bg-surface-2 px-3 text-sm outline-none focus:border-brand";

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
    <Sheet open={open} onClose={onClose} title="Transferir a otra área">
      <p className="mb-3 text-sm text-ink-2">
        El caso vuelve a la cola del área elegida y deja de estar asignado a usted.
      </p>
      <label className="mb-1 block text-sm font-medium" htmlFor="transfer-area">
        Área
      </label>
      <select
        id="transfer-area"
        className={selectClass}
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
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button
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
  const toast = useToast();
  const [reasonId, setReasonId] = useState<number | "">("");
  const reasons =
    catalog.data?.reasons.filter(
      (r) => r.area_id === null || r.area_id === conversation.area?.id,
    ) ?? [];

  return (
    <Sheet open={open} onClose={onClose} title="Cerrar caso">
      <label className="mb-1 block text-sm font-medium" htmlFor="close-reason">
        Motivo de contacto <span className="text-danger">*</span>
      </label>
      <select
        id="close-reason"
        className={selectClass}
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
      <p className="mt-2 text-xs text-ink-3">El motivo es obligatorio para los indicadores.</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button
          variant="primary"
          disabled={!reasonId || close.isPending}
          onClick={() =>
            reasonId &&
            close.mutate(reasonId, {
              onSuccess: () => {
                toast.ok("Caso cerrado");
                onClose();
              },
              onError: (e) => toast.error(e.message),
            })
          }
        >
          Cerrar caso
        </Button>
      </div>
    </Sheet>
  );
}
