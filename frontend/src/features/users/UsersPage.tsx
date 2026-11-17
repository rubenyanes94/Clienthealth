import { Mail, Plus } from "lucide-react";
import { useState } from "react";
import { useCatalog, useMe, useSaveUser, useSendAccess, useUsers } from "@/api/hooks";
import type { Access, Agent } from "@/api/types";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pill } from "@/components/ui/Pill";
import { useToast } from "@/components/ui/Toast";
import { formatDateTime } from "@/lib/format";
import { RequirePermission } from "../auth/RequirePermission";
import { AccessResultDialog } from "./AccessResultDialog";
import { ROLE_LABEL } from "./roles";
import { UserDialog } from "./UserDialog";

function ActiveToggle({ user }: { user: Agent }) {
  const save = useSaveUser(user.id);
  const toast = useToast();
  return (
    <Button
      size="sm"
      disabled={save.isPending}
      onClick={(event) => {
        event.stopPropagation();
        save.mutate(
          { is_active: !user.is_active },
          {
            onSuccess: () => toast.ok(user.is_active ? "Usuario desactivado" : "Usuario activado"),
            onError: (e) => toast.error(e.message),
          },
        );
      }}
    >
      {user.is_active ? "Desactivar" : "Activar"}
    </Button>
  );
}

function UsersList() {
  const me = useMe();
  const users = useUsers();
  const sendAccess = useSendAccess();
  const toast = useToast();
  const [access, setAccess] = useState<{ result: Access; agent: Agent } | null>(null);

  /** Si el correo salió, basta un aviso; si no, se explica qué pasó (o, en pruebas, el enlace). */
  const showAccess = (result: Access, agent: Agent) => {
    if (result.email_sent) toast.ok(`Correo enviado a ${agent.email}`);
    else setAccess({ result, agent });
  };
  const resend = (agent: Agent) =>
    sendAccess.mutate(agent.id, {
      onSuccess: (result) => showAccess(result, agent),
      onError: (e) => toast.error(e.message),
    });
  const catalog = useCatalog();
  const [dialog, setDialog] = useState<Agent | "new" | null>(null);

  const areaName = (id: number | null) =>
    id === null ? "Todas" : (catalog.data?.areas.find((a) => a.id === id)?.name ?? "—");

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-3 py-3 sm:px-4 md:py-0">
        <PageHeader
          title="Usuarios"
          subtitle="Cada persona tiene su cuenta: lo que hace queda registrado a su nombre."
        >
          <Button size="lg" variant="primary" onClick={() => setDialog("new")}>
            <Plus className="size-5" aria-hidden /> Nuevo usuario
          </Button>
        </PageHeader>
        <div className="mb-3 overflow-x-auto rounded-3xl bg-surface shadow-card">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="text-xs text-ink-3">
              <tr className="border-b border-line">
                <th className="px-4 py-4 font-medium">Usuario</th>
                <th className="px-4 py-4 font-medium">Rol y área</th>
                <th className="px-4 py-4 font-medium">Última actividad</th>
                <th className="px-4 py-4 font-medium">Estado</th>
                <th className="px-4 py-4" aria-hidden />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {users.data?.map((u) => (
                <tr
                  key={u.id}
                  onClick={() => setDialog(u)}
                  className="cursor-pointer transition hover:bg-surface-2 active:bg-surface-3"
                >
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-3">
                      <Avatar name={u.name} size="sm" />
                      <div className="min-w-0">
                        <div className="truncate font-semibold">{u.name}</div>
                        <div className="truncate text-xs text-ink-3">{u.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="text-ink-2">{ROLE_LABEL[u.role]}</div>
                    <div className="text-xs text-ink-3">{areaName(u.area_id)}</div>
                  </td>
                  <td className="px-4 py-4 text-ink-3 tabular-nums">
                    {u.last_seen_at ? formatDateTime(u.last_seen_at) : "Nunca"}
                  </td>
                  <td className="px-4 py-4">
                    {!u.is_active ? (
                      <Pill tone="neutral">Inactivo</Pill>
                    ) : u.password_set_at ? (
                      <Pill tone="ok">Activo</Pill>
                    ) : (
                      <Pill tone="warn">Invitación pendiente</Pill>
                    )}
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex justify-end gap-2">
                      {u.is_active && !u.password_set_at && (
                        <Button
                          size="sm"
                          disabled={sendAccess.isPending}
                          onClick={(event) => {
                            event.stopPropagation();
                            resend(u);
                          }}
                        >
                          <Mail className="size-3.5" aria-hidden /> Reenviar
                        </Button>
                      )}
                      {u.id !== me.data?.id && <ActiveToggle user={u} />}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.isPending && <p className="p-6 text-sm text-ink-3">Cargando…</p>}
          {users.error && <p className="p-6 text-sm text-danger">{users.error.message}</p>}
        </div>
      </div>
      <UserDialog
        open={dialog === "new"}
        onClose={() => setDialog(null)}
        onAccess={showAccess}
        onSendAccess={resend}
      />
      <UserDialog
        open={dialog !== null && dialog !== "new"}
        onClose={() => setDialog(null)}
        user={dialog !== null && dialog !== "new" ? dialog : undefined}
        onAccess={showAccess}
        onSendAccess={resend}
      />
      <AccessResultDialog
        result={access?.result ?? null}
        email={access?.agent.email ?? ""}
        onClose={() => setAccess(null)}
        onRetry={() => {
          const agent = access?.agent;
          setAccess(null);
          if (agent) resend(agent);
        }}
      />
    </div>
  );
}

export function UsersPage() {
  return (
    <RequirePermission
      permission="users.manage"
      message="Los usuarios los gestiona un administrador."
    >
      <UsersList />
    </RequirePermission>
  );
}
