import { ChevronRight } from "lucide-react";
import { Link } from "react-router";
import { useMyTasks } from "@/api/hooks";
import { Pill } from "@/components/ui/Pill";
import { TASK_ICON, TASK_LABEL } from "./tasks";

/** Lo que otras personas le asignaron a quien tiene la sesión. Si no hay nada, no ocupa espacio. */
export function MyTasks() {
  const tasks = useMyTasks();
  if (!tasks.data?.length) return null;
  return (
    <section aria-label="Mis tareas" className="mb-4 rounded-3xl bg-surface p-5 shadow-card sm:p-6">
      <h2 className="mb-3 text-sm font-semibold">Mis tareas pendientes ({tasks.data.length})</h2>
      <ul className="grid gap-2 lg:grid-cols-2">
        {tasks.data.map((t) => {
          const Icon = TASK_ICON[t.type];
          return (
            <li key={t.id}>
              <Link
                to={`/casos/${t.case.id}`}
                className="flex items-center gap-3 rounded-2xl p-3 ring-1 ring-line transition ring-inset hover:bg-surface-2 active:bg-surface-3"
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-ink text-white">
                  <Icon className="size-4" aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-1.5">
                    <span className="font-semibold">
                      {TASK_LABEL[t.type]} a {t.case.patient.first_name} {t.case.patient.last_name}
                    </span>
                    {t.priority === "high" && <Pill tone="danger">Urgente</Pill>}
                  </span>
                  <span className="block truncate text-sm text-ink-3">
                    #{t.case.id} · {t.case.subject}
                  </span>
                </span>
                <ChevronRight className="size-4 shrink-0 text-ink-3" aria-hidden />
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
