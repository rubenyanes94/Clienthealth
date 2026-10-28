import { useState } from "react";
import { useSimulateInbound } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { fieldClass, Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";

const inputClass = fieldClass;

/** Solo fuera de producción: inyecta un mensaje con el formato del webhook de Meta. */
export function SimulatorDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const simulate = useSimulateInbound();
  const toast = useToast();
  const [waId, setWaId] = useState("584140000000");
  const [name, setName] = useState("Paciente de prueba");
  const [text, setText] = useState("Hola, buenos días");

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Simular mensaje de WhatsApp"
      description="Solo fuera de producción. Entra por el mismo flujo que un mensaje real de Meta."
    >
      <div className="space-y-3">
        <div>
          <label className="mb-1.5 block text-sm font-medium" htmlFor="sim-phone">
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
          <label className="mb-1.5 block text-sm font-medium" htmlFor="sim-name">
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
          <label className="mb-1.5 block text-sm font-medium" htmlFor="sim-text">
            Mensaje
          </label>
          <textarea
            id="sim-text"
            rows={3}
            className={`${fieldClass} h-auto py-3`}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>
      </div>
      <div className="mt-7 grid grid-cols-2 gap-2.5">
        <Button size="lg" onClick={onClose}>
          Cerrar
        </Button>
        <Button
          size="lg"
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
