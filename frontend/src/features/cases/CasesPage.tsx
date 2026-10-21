import { useNavigate, useSearchParams } from "react-router";
import { useInbox } from "@/api/hooks";
import type { InboxFilter } from "@/api/types";
import { Avatar } from "@/components/ui/Avatar";
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
  const filter = OPTIONS.find((o) => o.value === search.get("filtro"))?.value ?? "all";
  const cases = useInbox(filter);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">Casos</h1>
            <p className="mt-1 text-sm text-ink-3">Historial de conversaciones y su estado.</p>
          </div>
          <Segmented
            label="Estado de los casos"
            options={OPTIONS}
            value={filter}
            onChange={(f) => setSearch({ filtro: f })}
          />
        </div>
        <div className="overflow-x-auto rounded-2xl bg-surface shadow-card ring-1 ring-line">
          <table className="w-full min-w-[46rem] text-left text-sm">
            <thead className="bg-surface-2 text-[11px] tracking-wider text-ink-3 uppercase">
              <tr>
                <th className="px-5 py-3 font-semibold">Caso</th>
                <th className="px-5 py-3 font-semibold">Paciente</th>
                <th className="px-5 py-3 font-semibold">Área</th>
                <th className="px-5 py-3 font-semibold">Estado</th>
                <th className="px-5 py-3 font-semibold">Agente</th>
                <th className="px-5 py-3 font-semibold">Última actividad</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {cases.data?.items.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/casos/${c.id}`)}
                  className="cursor-pointer transition hover:bg-surface-2"
                >
                  <td className="px-5 py-3.5 font-medium text-ink-3 tabular-nums">#{c.id}</td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <Avatar name={c.contact.name} size="sm" urgent={c.is_urgent} />
                      <a
                        href={`/casos/${c.id}`}
                        onClick={(e) => e.preventDefault()}
                        className="font-medium hover:underline"
                      >
                        {contactName(c)}
                      </a>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-ink-2">{c.area?.name ?? "—"}</td>
                  <td className="px-5 py-3.5">
                    <div className="flex gap-1">
                      {c.is_urgent && <UrgentPill />}
                      <StatusPill status={c.status} />
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-ink-2">{c.assigned_agent?.name ?? "—"}</td>
                  <td className="px-5 py-3.5 text-ink-3 tabular-nums">
                    {c.last_message_at ? formatDateTime(c.last_message_at) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {cases.isPending && <p className="p-5 text-sm text-ink-3">Cargando…</p>}
          {cases.data?.items.length === 0 && (
            <p className="p-10 text-center text-sm text-ink-3">Sin casos.</p>
          )}
        </div>
      </div>
    </div>
  );
}
