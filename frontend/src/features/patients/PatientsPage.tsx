import { ChevronRight, Plus, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";
import { usePatientSearch } from "@/api/hooks";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { fieldClass } from "@/components/ui/Sheet";
import { displayPhone } from "@/lib/format";
import { useDebounced } from "@/lib/useDebounced";
import { PatientDialog } from "./PatientDialog";

export function PatientsPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);
  const patients = usePatientSearch(useDebounced(q));

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-3 py-3 sm:px-4 md:py-0">
        <PageHeader title="Pacientes" subtitle="Registre al paciente y luego cree sus casos.">
          <Button size="lg" variant="primary" onClick={() => setCreating(true)}>
            <Plus className="size-5" aria-hidden /> Nuevo paciente
          </Button>
        </PageHeader>

        <div className="relative mb-4">
          <Search
            className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-ink-3"
            aria-hidden
          />
          <label className="sr-only" htmlFor="patient-search">
            Buscar paciente
          </label>
          <input
            id="patient-search"
            type="search"
            autoComplete="off"
            placeholder="Buscar por nombre, cédula, teléfono o correo…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className={`${fieldClass} bg-surface pl-12 shadow-card ring-transparent`}
          />
        </div>

        <div className="mb-3 overflow-x-auto rounded-3xl bg-surface shadow-card">
          <table className="w-full min-w-[42rem] text-left text-sm">
            <thead className="text-xs text-ink-3">
              <tr className="border-b border-line">
                <th className="px-6 py-4 font-medium">Paciente</th>
                <th className="px-6 py-4 font-medium">Cédula</th>
                <th className="px-6 py-4 font-medium">Teléfono</th>
                <th className="px-6 py-4 font-medium">Correo</th>
                <th className="w-10" aria-hidden />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {patients.data?.items.map((p) => (
                <tr
                  key={p.id}
                  onClick={() => navigate(`/pacientes/${p.id}`)}
                  className="group cursor-pointer transition hover:bg-surface-2 active:bg-surface-3"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <Avatar name={`${p.first_name} ${p.last_name}`} size="sm" />
                      <a
                        href={`/pacientes/${p.id}`}
                        onClick={(e) => e.preventDefault()}
                        className="font-semibold hover:underline"
                      >
                        {p.first_name} {p.last_name}
                      </a>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-ink-2 tabular-nums">{p.national_id}</td>
                  <td className="px-6 py-4 text-ink-2 tabular-nums">{displayPhone(p.phone)}</td>
                  <td className="px-6 py-4 text-ink-2">{p.email}</td>
                  <td className="pr-5">
                    <span className="flex size-8 items-center justify-center rounded-full bg-surface-3 text-ink-3 transition group-hover:bg-ink group-hover:text-white">
                      <ChevronRight className="size-4" aria-hidden />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {patients.isPending && <p className="p-6 text-sm text-ink-3">Cargando…</p>}
          {patients.error && <p className="p-6 text-sm text-danger">{patients.error.message}</p>}
          {patients.data?.items.length === 0 && (
            <p className="p-12 text-center text-sm text-ink-3">
              {q
                ? "Ningún paciente coincide con la búsqueda."
                : "Aún no hay pacientes registrados."}
            </p>
          )}
        </div>
      </div>
      <PatientDialog open={creating} onClose={() => setCreating(false)} />
    </div>
  );
}
