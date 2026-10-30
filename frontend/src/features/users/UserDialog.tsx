import { useState } from "react";
import { useCatalog, useMe, useSaveUser } from "@/api/hooks";
import type { Agent, AgentRole } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Segmented } from "@/components/ui/Segmented";
import { fieldClass, Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";
import { MIN_PASSWORD, ROLE_LABEL, ROLES } from "./roles";

function UserForm({ user, onClose }: { user?: Agent; onClose: () => void }) {
  const me = useMe();
  const catalog = useCatalog();
  const save = useSaveUser(user?.id);
  const toast = useToast();
  const isSelf = user?.id === me.data?.id;

  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [role, setRole] = useState<AgentRole>(user?.role ?? "agent");
  const [areaId, setAreaId] = useState<number | "">(user?.area_id ?? "");
  const [password, setPassword] = useState("");

  const passwordOk = user
    ? password === "" || password.length >= MIN_PASSWORD
    : password.length >= MIN_PASSWORD;
  const valid =
    name.trim().length >= 2 &&
    (user !== undefined || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) &&
    passwordOk;

  const submit = () => {
    const common = { name: name.trim(), role, area_id: areaId === "" ? null : areaId };
    const body = user
      ? { ...common, ...(password ? { password } : {}) }
      : { ...common, email: email.trim(), password };
    save.mutate(body, {
      onSuccess: () => {
        toast.ok(user ? "Usuario actualizado" : "Usuario creado");
        onClose();
      },
    });
  };

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nombre y apellido" htmlFor="user-name" required>
          <input
            id="user-name"
            autoComplete="off"
            className={fieldClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field label="Correo" htmlFor="user-email" required={!user}>
          <input
            id="user-email"
            type="email"
            autoComplete="off"
            disabled={Boolean(user)}
            className={`${fieldClass} disabled:opacity-60`}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Field>
        <Field label="Área" htmlFor="user-area">
          <select
            id="user-area"
            className={fieldClass}
            value={areaId}
            onChange={(e) => setAreaId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Sin área (todas)</option>
            {catalog.data?.areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label={user ? "Contraseña nueva (opcional)" : "Contraseña inicial"}
          htmlFor="user-password"
          required={!user}
          error={
            password && password.length < MIN_PASSWORD
              ? `Mínimo ${MIN_PASSWORD} caracteres`
              : undefined
          }
        >
          <input
            id="user-password"
            type="password"
            autoComplete="new-password"
            className={fieldClass}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        <div className="sm:col-span-2">
          <span className="mb-1.5 block text-sm font-medium">Rol</span>
          {isSelf ? (
            <p className="text-sm text-ink-3">
              {ROLE_LABEL[role]}. No puede cambiar su propio rol.
            </p>
          ) : (
            <Segmented
              label="Rol"
              options={ROLES.map((r) => ({ value: r, label: ROLE_LABEL[r] }))}
              value={role}
              onChange={setRole}
            />
          )}
        </div>
      </div>
      <p className="mt-4 text-sm text-ink-3">
        Pídale a la persona que cambie su contraseña en «Mi cuenta» al entrar por primera vez.
      </p>
      {save.error && (
        <p role="alert" className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
          {save.error.message}
        </p>
      )}
      <div className="mt-7 grid grid-cols-2 gap-2.5">
        <Button size="lg" onClick={onClose}>
          Cancelar
        </Button>
        <Button size="lg" variant="primary" disabled={!valid || save.isPending} onClick={submit}>
          Guardar
        </Button>
      </div>
    </>
  );
}

export function UserDialog({
  open,
  onClose,
  user,
}: {
  open: boolean;
  onClose: () => void;
  user?: Agent;
}) {
  return (
    <Sheet
      open={open}
      onClose={onClose}
      size="lg"
      title={user ? "Editar usuario" : "Nuevo usuario"}
    >
      <UserForm user={user} onClose={onClose} />
    </Sheet>
  );
}
