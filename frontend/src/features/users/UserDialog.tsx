import { useState } from "react";
import { useCatalog, useCreateUser, useMe, useSaveUser } from "@/api/hooks";
import { Mail } from "lucide-react";
import type { Access, Agent, AgentRole } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Segmented } from "@/components/ui/Segmented";
import { fieldClass, Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/Toast";
import { ROLE_LABEL, ROLES } from "./roles";

function UserForm({
  user,
  onClose,
  onAccess,
  onSendAccess,
}: {
  user?: Agent;
  onClose: () => void;
  onAccess: (access: Access, agent: Agent) => void;
  onSendAccess: (agent: Agent) => void;
}) {
  const me = useMe();
  const catalog = useCatalog();
  const update = useSaveUser(user?.id ?? 0);
  const create = useCreateUser();
  const save = user ? update : create;
  const toast = useToast();
  const isSelf = user?.id === me.data?.id;

  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [role, setRole] = useState<AgentRole>(user?.role ?? "agent");
  const [areaId, setAreaId] = useState<number | "">(user?.area_id ?? "");
  const valid =
    name.trim().length >= 2 && (user !== undefined || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email));

  const submit = () => {
    const common = { name: name.trim(), role, area_id: areaId === "" ? null : areaId };
    if (user) {
      update.mutate(common, {
        onSuccess: () => {
          toast.ok("Usuario actualizado");
          onClose();
        },
      });
      return;
    }
    create.mutate(
      { ...common, email: email.trim() },
      {
        onSuccess: (created) => {
          if (created.access) onAccess(created.access, created.agent);
          onClose();
        },
      },
    );
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
      {user ? (
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-3xl bg-surface-2 p-4">
          <p className="max-w-xs text-sm text-ink-2">
            {user.password_set_at
              ? "Le enviaremos un enlace para que cree una contraseña nueva."
              : "Aún no ha creado su contraseña. Puede reenviarle la invitación."}
          </p>
          <Button
            disabled={!user.is_active}
            onClick={() => {
              onSendAccess(user);
              onClose();
            }}
          >
            <Mail className="size-4" aria-hidden />
            {user.password_set_at ? "Enviar enlace" : "Reenviar invitación"}
          </Button>
        </div>
      ) : (
        <p className="mt-4 rounded-2xl bg-surface-2 px-4 py-3 text-sm text-ink-2">
          Le enviaremos un correo a <strong>{email.trim() || "la persona"}</strong> para que cree su
          contraseña. Nadie más la conocerá, tampoco usted.
        </p>
      )}
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
          {user ? "Guardar" : save.isPending ? "Enviando…" : "Crear y enviar invitación"}
        </Button>
      </div>
    </>
  );
}

export function UserDialog({
  open,
  onClose,
  user,
  onAccess,
  onSendAccess,
}: {
  open: boolean;
  onClose: () => void;
  user?: Agent;
  onAccess: (access: Access, agent: Agent) => void;
  onSendAccess: (agent: Agent) => void;
}) {
  return (
    <Sheet
      open={open}
      onClose={onClose}
      size="lg"
      title={user ? "Editar usuario" : "Nuevo usuario"}
    >
      <UserForm user={user} onClose={onClose} onAccess={onAccess} onSendAccess={onSendAccess} />
    </Sheet>
  );
}
