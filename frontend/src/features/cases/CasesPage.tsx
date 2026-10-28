import { ChevronRight } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router";
import { useInbox } from "@/api/hooks";
import type { InboxFilter } from "@/api/types";
import { Avatar } from "@/components/ui/Avatar";
import { PageHeader } from "@/components/ui/PageHeader";
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
      <div className="mx-auto max-w-6xl px-3 py-3 sm:px-4 md:py-0">
        <PageHeader title="Casos" subtitle="Historial de conversaciones y su estado.">
          <Segmented
            label="Estado de los casos"
            options={OPTIONS}
            value={filter}
            onChange={(f) => setSearch({ filtro: f })}
          />
        </PageHeader>
        <div className="overflow-x-auto rounded-3xl bg-surface shadow-card">
          <table className="w-full min-w-[46rem] text-left text-sm">
            <thead className="text-xs text-ink-3">
              <tr className="border-b border-line">
                <th className="px-6 py-4 font-medium">Caso</th>
                <th className="px-6 py-4 font-medium">Paciente</th>
                <th className="px-6 py-4 font-medium">Área</th>
                <th className="px-6 py-4 font-medium">Estado</th>
                <th className="px-6 py-4 font-medium">Agente</th>
                <th className="px-6 py-4 font-medium">Última actividad</th>
                <th className="w-10" aria-hidden />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {cases.data?.items.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/casos/${c.id}`)}
                  className="group cursor-pointer transition hover:bg-surface-2 active:bg-surface-3"
                >
                  <td className="px-6 py-4 font-medium text-ink-3 tabular-nums">#{c.id}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <Avatar name={c.contact.name} size="sm" urgent={c.is_urgent} />
                      <a
                        href={`/casos/${c.id}`}
                        onClick={(e) => e.preventDefault()}
                        className="font-semibold hover:underline"
                      >
                        {contactName(c)}
                      </a>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-ink-2">{c.area?.name ?? "—"}</td>
                  <td className="px-6 py-4">
                    <div className="flex gap-1">
                      {c.is_urgent && <UrgentPill />}
                      <StatusPill status={c.status} />
                    </div>
                  </td>
                  <td className="px-6 py-4 text-ink-2">{c.assigned_agent?.name ?? "—"}</td>
                  <td className="px-6 py-4 text-ink-3 tabular-nums">
                    {c.last_message_at ? formatDateTime(c.last_message_at) : "—"}
                  </td>
                  <td className="pr-5">
                    <span className="flex size-8 items-center justify-center rounded-full bg-surface-3 text-ink-3 transition group-hover:bg-ink group-hover:text-white">
                      <ChevronRight className="size-4" aria-hidden />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {cases.isPending && <p className="p-6 text-sm text-ink-3">Cargando…</p>}
          {cases.data?.items.length === 0 && (
            <p className="p-12 text-center text-sm text-ink-3">Sin casos.</p>
          )}
        </div>
      </div>
    </div>
  );
}
