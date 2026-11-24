import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { Shell } from "./components/Shell";
import { Spinner } from "./components/ui";
import { LoginPage } from "./pages/Login";
import { DashboardPage } from "./pages/Dashboard";
import { TrainsPage } from "./pages/Trains";
import { NetworkPage } from "./pages/Network";
import { ConflictsPage } from "./pages/Conflicts";
import { RecommendationsPage } from "./pages/Recommendations";
import { RecommendationDetailPage } from "./pages/RecommendationDetail";
import { DisruptionsPage } from "./pages/Disruptions";
import { WhatIfPage } from "./pages/WhatIf";
import { AnalyticsPage } from "./pages/Analytics";
import { AuditPage } from "./pages/Audit";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, initialising } = useAuth();
  if (initialising) return <Spinner label="Restoring session" />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireRole({
  roles,
  children,
}: {
  roles: string[];
  children: ReactNode;
}) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role)) {
    return (
      <div className="banner banner-danger" role="alert">
        Your role does not have access to this screen.
      </div>
    );
  }
  return <>{children}</>;
}

export function App() {
  const { user, initialising } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={
          initialising ? (
            <Spinner label="Restoring session" />
          ) : user ? (
            <Navigate to="/" replace />
          ) : (
            <LoginPage />
          )
        }
      />
      <Route
        element={
          <RequireAuth>
            <Shell />
          </RequireAuth>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="trains" element={<TrainsPage />} />
        <Route path="network" element={<NetworkPage />} />
        <Route path="conflicts" element={<ConflictsPage />} />
        <Route path="recommendations" element={<RecommendationsPage />} />
        <Route path="recommendations/:recommendationId" element={<RecommendationDetailPage />} />
        <Route
          path="disruptions"
          element={
            <RequireRole roles={["SECTION_MASTER"]}>
              <DisruptionsPage />
            </RequireRole>
          }
        />
        <Route path="what-if" element={<WhatIfPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route
          path="audit"
          element={
            <RequireRole roles={["SECTION_MASTER"]}>
              <AuditPage />
            </RequireRole>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
