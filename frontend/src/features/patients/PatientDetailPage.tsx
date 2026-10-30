import { ArrowLeft, ChevronRight, Pencil, Plus } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { usePatient } from "@/api/hooks";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { displayPhone, formatDateTime } from "@/lib/format";
import { NewCaseDialog } from "../cases/NewCaseDialog";
import { StagePill } from "../cases/StagePill";
import { PatientDialog } from "./PatientDialog";

export function PatientDetailPage() {
  const id = Number(useParams().id);
  const patient = usePatient(id);
  const [dialog, setDialog] = useState<"edit" | "case" | null>(null);
  const p = patient.data;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-3 py-3 sm:px-4 md:py-0">
        <Link
          to="/pacientes"
          className="mb-4 inline-flex h-11 items-center gap-2 rounded-full bg-surface px-5 text-sm font-medium text-ink-2 shadow-card transition hover:text-ink"
        >
          <ArrowLeft className="size-4" aria-hidden /> Pacientes
        </Link>
        {patient.error && <p className="text-sm text-danger">{patient.error.message}</p>}
        {p && (
          <>
            <div className="mb-4 rounded-3xl bg-surface p-6 shadow-card sm:p-8">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-5">
                  <Avatar name={`${p.first_name} ${p.last_name}`} size="lg" />
                  <div>
                    <p className="text-sm text-ink-3">Paciente</p>
                    <h1 className="text-3xl font-bold">
                      {p.first_name} {p.last_name}
                    </h1>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => setDialog("edit")}>
                    <Pencil className="size-4" aria-hidden /> Editar
                  </Button>
                  <Button variant="primary" onClick={() => setDialog("case")}>
                    <Plus className="size-4" aria-hidden /> Nuevo caso
                  </Button>
                </div>
              </div>
              <dl className="mt-6 grid gap-4 border-t border-line pt-5 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  ["Cédula", p.national_id],
                  ["Teléfono", displayPhone(p.phone)],
                  ["Correo", p.email],
                  ["Registrado", formatDateTime(p.created_at)],
                ].map(([label, value]) => (
                  <div key={label} className="min-w-0">
                    <dt className="text-xs text-ink-3">{label}</dt>
                    <dd className="mt-1 truncate text-[15px] font-medium">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>

            <section className="mb-3 rounded-3xl bg-surface p-6 shadow-card sm:p-8">
              <h2 className="mb-4 text-lg font-semibold">Casos ({p.cases.length})</h2>
              {p.cases.length === 0 ? (
                <p className="py-8 text-center text-sm text-ink-3">
                  Este paciente aún no tiene casos.
                </p>
              ) : (
                <ul className="space-y-2">
                  {p.cases.map((c) => (
                    <li key={c.id}>
                      <Link
                        to={`/casos/${c.id}`}
                        className="flex items-center gap-4 rounded-2xl p-4 ring-1 ring-line ring-inset transition hover:bg-surface-2 active:bg-surface-3"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="truncate font-medium">{c.subject}</div>
                          <div className="mt-1 truncate text-sm text-ink-3">
                            #{c.id} · {c.area.name} · {formatDateTime(c.opened_at)}
                          </div>
                        </div>
                        <StagePill stage={c.stage} />
                        <ChevronRight className="size-4 shrink-0 text-ink-3" aria-hidden />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <PatientDialog open={dialog === "edit"} onClose={() => setDialog(null)} patient={p} />
            <NewCaseDialog open={dialog === "case"} onClose={() => setDialog(null)} patient={p} />
          </>
        )}
      </div>
    </div>
  );
}
