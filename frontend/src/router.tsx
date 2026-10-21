import { createBrowserRouter, Navigate } from "react-router";
import { AppShell } from "./AppShell";
import { LoginPage } from "./features/auth/LoginPage";
import { RequireAuth } from "./features/auth/RequireAuth";
import { CaseDetailPage } from "./features/cases/CaseDetailPage";
import { CasesPage } from "./features/cases/CasesPage";
import { InboxPage } from "./features/inbox/InboxPage";
import { LazyPanelsPage, LazyReportsPage } from "./features/metrics/lazy";
import { Placeholder } from "./features/metrics/Placeholder";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/conversaciones" replace /> },
      { path: "conversaciones", element: <InboxPage /> },
      { path: "conversaciones/:id", element: <InboxPage /> },
      { path: "casos", element: <CasesPage /> },
      { path: "casos/:id", element: <CaseDetailPage /> },
      {
        path: "paneles",
        element: <LazyPanelsPage />,
      },
      {
        path: "informes",
        element: <LazyReportsPage />,
      },
      { path: "contactos", element: <Placeholder title="Contactos" phase="fase 4" /> },
      { path: "*", element: <Navigate to="/conversaciones" replace /> },
    ],
  },
]);
