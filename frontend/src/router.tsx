import { createBrowserRouter, Navigate } from "react-router";
import { AppShell } from "./AppShell";
import { LoginPage } from "./features/auth/LoginPage";
import { RequireAuth } from "./features/auth/RequireAuth";
import { CaseDetailPage } from "./features/cases/CaseDetailPage";
import { CasesPage } from "./features/cases/CasesPage";
import { ConversationLogPage } from "./features/inbox/ConversationLogPage";
import { InboxPage } from "./features/inbox/InboxPage";
import { PatientDetailPage } from "./features/patients/PatientDetailPage";
import { PatientsPage } from "./features/patients/PatientsPage";
import { UsersPage } from "./features/users/UsersPage";
import { LazyPanelsPage, LazyReportsPage } from "./features/metrics/lazy";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/casos" replace /> },
      { path: "conversaciones", element: <InboxPage /> },
      { path: "conversaciones/:id", element: <InboxPage /> },
      { path: "conversaciones/:id/registro", element: <ConversationLogPage /> },
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
      { path: "pacientes", element: <PatientsPage /> },
      { path: "pacientes/:id", element: <PatientDetailPage /> },
      { path: "usuarios", element: <UsersPage /> },
      { path: "contactos", element: <Navigate to="/pacientes" replace /> },
      { path: "*", element: <Navigate to="/casos" replace /> },
    ],
  },
]);
