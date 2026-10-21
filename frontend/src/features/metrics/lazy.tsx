import { lazy, Suspense } from "react";

// Los paneles cargan Recharts: se descargan solo al abrirlos (los agentes no los usan).
const PanelsPage = lazy(() => import("./PanelsPage").then((m) => ({ default: m.PanelsPage })));
const ReportsPage = lazy(() => import("./ReportsPage").then((m) => ({ default: m.ReportsPage })));

const fallback = <p className="p-8 text-sm text-ink-3">Cargando…</p>;

export function LazyPanelsPage() {
  return (
    <Suspense fallback={fallback}>
      <PanelsPage />
    </Suspense>
  );
}

export function LazyReportsPage() {
  return (
    <Suspense fallback={fallback}>
      <ReportsPage />
    </Suspense>
  );
}
