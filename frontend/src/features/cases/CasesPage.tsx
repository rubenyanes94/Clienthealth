import { useNavigate, useSearchParams } from "react-router";
import { useInbox } from "@/api/hooks";
import type { InboxFilter } from "@/api/types";
import { Segmented } from "@/components/ui/Segmented";
import { formatDateTime } from "@/lib/format";
import { StatusPill, UrgentPill } from "../inbox/bits";
import { contactName } from "../inbox/permissions";

const OPTIONS: { value: InboxFilter; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "open", label: "Abiertos" },
  { value: "pending", label: "En espera" },
  { value: "closed", label: "Cerrados" },
];

export function CasesPage() {
  const [search, setSearch] = useSearchParams();
  const navigate = useNavigate();
  const filter = (OPTIONS.find((o) => o.value === search.get("filtro"))?.value ??
    "all") as InboxFilter;
  const cases = useInbox(filter);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-lg font-semibold">Casos</h1>
          <Segmented
            label="Estado de los casos"
            options={OPTIONS}
            value={filter}
            onChange={(f) => setSearch({ filtro: f })}
          />
        </div>
        <div className="overflow-x-auto rounded-card border border-line bg-surface shadow-card">
          <table className="w-full min-w-[44rem] text-left text-sm">
            <thead className="border-b border-line text-xs text-ink-3">
              <tr>
                <th className="px-4 py-2.5 font-medium">#</th>
                <th className="px-4 py-2.5 font-medium">Paciente</th>
                <th className="px-4 py-2.5 font-medium">Área</th>
                <th className="px-4 py-2.5 font-medium">Estado</th>
                <th className="px-4 py-2.5 font-medium">Agente</th>
                <th className="px-4 py-2.5 font-medium">Abierto</th>
                <th className="px-4 py-2.5 font-medium">Última actividad</th>
              </tr>
            </thead>
            <tbody>
              {cases.data?.items.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/casos/${c.id}`)}
                  className="cursor-pointer border-b border-line last:border-0 hover:bg-surface-2"
                >
                  <td className="px-4 py-2.5 text-ink-3 tabular-nums">{c.id}</td>
                  <td className="px-4 py-2.5 font-medium">
                    <a
                      href={`/casos/${c.id}`}
                      onClick={(e) => e.preventDefault()}
                      className="hover:underline"
                    >
                      {contactName(c)}
                    </a>
                  </td>
                  <td className="px-4 py-2.5">{c.area?.name ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex gap-1">
                      {c.is_urgent && <UrgentPill />}
                      <StatusPill status={c.status} />
                    </div>
                  </td>
                  <td className="px-4 py-2.5">{c.assigned_agent?.name ?? "—"}</td>
                  <td className="px-4 py-2.5 text-ink-2">{formatDateTime(c.opened_at)}</td>
                  <td className="px-4 py-2.5 text-ink-2">
                    {c.last_message_at ? formatDateTime(c.last_message_at) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {cases.isPending && <p className="p-4 text-sm text-ink-3">Cargando…</p>}
          {cases.data?.items.length === 0 && (
            <p className="p-6 text-center text-sm text-ink-3">Sin casos.</p>
          )}
        </div>
      </div>
    </div>
  );
}
