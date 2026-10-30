import { useState } from "react";
import { useCatalog, useChangePassword, useMe } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { fieldClass, Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";
import { MIN_PASSWORD, ROLE_LABEL } from "./roles";

function AccountForm({ onClose }: { onClose: () => void }) {
  const me = useMe();
  const catalog = useCatalog();
  const change = useChangePassword();
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");

  const tooShort = next.length > 0 && next.length < MIN_PASSWORD;
  const mismatch = repeat.length > 0 && repeat !== next;
  const area = catalog.data?.areas.find((a) => a.id === me.data?.area_id)?.name;

  return (
    <>
      <dl className="mb-6 divide-y divide-line rounded-3xl bg-surface-2 px-4 ring-1 ring-line ring-inset">
        {[
          ["Nombre", me.data?.name],
          ["Correo", me.data?.email],
          ["Rol", me.data ? ROLE_LABEL[me.data.role] : ""],
          ["Área", area ?? "Todas"],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 py-3 text-sm">
            <dt className="text-ink-3">{label}</dt>
            <dd className="truncate font-medium">{value}</dd>
          </div>
        ))}
      </dl>

      <h3 className="mb-1 text-sm font-semibold">Cambiar contraseña</h3>
      <p className="mb-4 text-sm text-ink-3">
        Todo lo que se haga con esta cuenta queda registrado a su nombre: no la comparta.
      </p>
      <div className="space-y-4">
        <Field label="Contraseña actual" htmlFor="account-current" required>
          <input
            id="account-current"
            type="password"
            autoComplete="current-password"
            className={fieldClass}
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
        </Field>
        <Field
          label="Contraseña nueva"
          htmlFor="account-new"
          required
          error={tooShort ? `Mínimo ${MIN_PASSWORD} caracteres` : undefined}
        >
          <input
            id="account-new"
            type="password"
            autoComplete="new-password"
            className={fieldClass}
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
        </Field>
        <Field
          label="Repita la contraseña nueva"
          htmlFor="account-repeat"
          required
          error={mismatch ? "No coincide" : undefined}
        >
          <input
            id="account-repeat"
            type="password"
            autoComplete="new-password"
            className={fieldClass}
            value={repeat}
            onChange={(e) => setRepeat(e.target.value)}
          />
        </Field>
      </div>
      {change.error && (
        <p role="alert" className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {change.error.message}
        </p>
      )}
      <div className="mt-7 grid grid-cols-2 gap-2.5">
        <Button size="lg" onClick={onClose}>
          Cerrar
        </Button>
        <Button
          size="lg"
          variant="primary"
          disabled={!current || next.length < MIN_PASSWORD || next !== repeat || change.isPending}
          onClick={() =>
            change.mutate(
              { current_password: current, new_password: next },
              {
                onSuccess: () => {
                  toast.ok("Contraseña actualizada");
                  onClose();
                },
              },
            )
          }
        >
          Guardar
        </Button>
      </div>
    </>
  );
}

export function AccountDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Sheet open={open} onClose={onClose} title="Mi cuenta">
      <AccountForm onClose={onClose} />
    </Sheet>
  );
}
