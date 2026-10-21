import { useState } from "react";
import { useSimulateInbound } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";

const inputClass =
  "h-10 w-full rounded-lg border border-line bg-surface-2 px-3 text-sm outline-none focus:border-brand";

/** Solo fuera de producción: inyecta un mensaje con el formato del webhook de Meta. */
export function SimulatorDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const simulate = useSimulateInbound();
  const toast = useToast();
  const [waId, setWaId] = useState("584140000000");
  const [name, setName] = useState("Paciente de prueba");
  const [text, setText] = useState("Hola, buenos días");

  return (
    <Sheet open={open} onClose={onClose} title="Simular mensaje de WhatsApp">
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium" htmlFor="sim-phone">
            Número (wa_id)
          </label>
          <input
            id="sim-phone"
            className={inputClass}
            value={waId}
            onChange={(e) => setWaId(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium" htmlFor="sim-name">
            Nombre del perfil
          </label>
          <input
            id="sim-name"
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium" htmlFor="sim-text">
            Mensaje
          </label>
          <textarea
            id="sim-text"
            rows={3}
            className="w-full rounded-lg border border-line bg-surface-2 px-3 py-2 text-sm outline-none focus:border-brand"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cerrar
        </Button>
        <Button
          variant="primary"
          disabled={!text.trim() || simulate.isPending}
          onClick={() =>
            simulate.mutate(
              { wa_id: waId, name: name || null, text },
              {
                onSuccess: () => {
                  toast.ok("Mensaje recibido");
                  setText("");
                },
                onError: (e) => toast.error(e.message),
              },
            )
          }
        >
          Enviar como paciente
        </Button>
      </div>
    </Sheet>
  );
}
