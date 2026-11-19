import { RefreshCw, Search, Stethoscope } from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";
import { useDirectory } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Segmented } from "@/components/ui/Segmented";
import { fieldClass } from "@/components/ui/Sheet";
import { formatDateTime } from "@/lib/format";
import { useCan } from "../auth/permissions";
import { DoctorCard } from "./DoctorCard";
import { ImportDialog } from "./ImportDialog";
import { buildingsOf, matches, specialtiesOf } from "./search";

const ALL = "todos";

export function DirectoryPage() {
  const can = useCan();
  const directory = useDirectory();
  const [query, setQuery] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [building, setBuilding] = useState(ALL);
  const [importing, setImporting] = useState(false);
  const deferred = useDeferredValue(query);

  const doctors = useMemo(() => directory.data?.doctors ?? [], [directory.data]);
  const buildings = useMemo(() => buildingsOf(doctors), [doctors]);
  const specialties = useMemo(() => specialtiesOf(doctors), [doctors]);
  const results = useMemo(
    () =>
      doctors.filter(
        (d) =>
          matches(d, deferred) &&
          (!specialty || d.specialties.includes(specialty)) &&
          (building === ALL || d.offices.some((o) => o.building === building)),
      ),
    [doctors, deferred, specialty, building],
  );
  const last = directory.data?.last_import;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl px-3 py-3 sm:px-4 md:py-0">
        <PageHeader
          title="Directorio"
          subtitle="Encuentre rápido dónde queda el consultorio de cada médico."
        >
          {can("directory.manage") && (
            <Button size="lg" variant="primary" onClick={() => setImporting(true)}>
              <RefreshCw className="size-5" aria-hidden /> Actualizar
            </Button>
          )}
        </PageHeader>

        <div className="relative mb-3">
          <Search
            className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-ink-3"
            aria-hidden
          />
          <label className="sr-only" htmlFor="directory-search">
            Buscar médico, especialidad o consultorio
          </label>
          <input
            id="directory-search"
            type="search"
            autoComplete="off"
            autoFocus
            placeholder="Médico, especialidad o consultorio… (ej. «cardio», «anexo b 5»)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className={`${fieldClass} h-14 bg-surface pl-12 text-lg shadow-card ring-transparent`}
          />
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-3">
          {buildings.length > 1 && (
            <Segmented
              label="Edificio"
              options={[
                { value: ALL, label: "Todos" },
                ...buildings.map((b) => ({ value: b, label: b })),
              ]}
              value={building}
              onChange={setBuilding}
            />
          )}
          <label className="sr-only" htmlFor="directory-specialty">
            Especialidad
          </label>
          <select
            id="directory-specialty"
            value={specialty}
            onChange={(e) => setSpecialty(e.target.value)}
            className="h-11 max-w-full rounded-full bg-surface px-4 text-sm shadow-xs ring-1 ring-line outline-none ring-inset focus:ring-2 focus:ring-ink"
          >
            <option value="">Todas las especialidades</option>
            {specialties.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name} ({s.count})
              </option>
            ))}
          </select>
          <span className="text-sm text-ink-3">
            {results.length} de {doctors.length} médicos
            {last && ` · actualizado el ${formatDateTime(last.created_at)}`}
          </span>
        </div>

        {directory.isPending && <p className="p-6 text-sm text-ink-3">Cargando…</p>}
        {directory.error && <p className="p-6 text-sm text-danger">{directory.error.message}</p>}
        {directory.data && doctors.length === 0 && (
          <div className="flex flex-col items-center gap-3 rounded-3xl bg-surface px-6 py-16 text-center shadow-card">
            <span className="flex size-14 items-center justify-center rounded-full bg-ink text-white">
              <Stethoscope className="size-6" aria-hidden />
            </span>
            <p className="max-w-sm text-sm text-ink-3">
              {can("directory.manage")
                ? "El directorio está vacío. Tráigalo desde la web del centro con «Actualizar»."
                : "El directorio aún no está cargado. Pídale a un administrador que lo actualice."}
            </p>
          </div>
        )}
        {doctors.length > 0 && results.length === 0 && (
          <p className="rounded-3xl bg-surface px-6 py-12 text-center text-sm text-ink-3 shadow-card">
            Ningún médico coincide con la búsqueda.
          </p>
        )}
        <div className="grid gap-3 pb-3 md:grid-cols-2 xl:grid-cols-3">
          {results.map((d) => (
            <DoctorCard key={d.id} doctor={d} />
          ))}
        </div>
      </div>
      {can("directory.manage") && (
        <ImportDialog open={importing} onClose={() => setImporting(false)} />
      )}
    </div>
  );
}
