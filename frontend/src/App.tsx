import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { Shell } from "./components/Shell";
import { Spinner } from "./components/ui";
import { LoginPage } from "./pages/Login";
import { DashboardPage } from "./pages/Dashboard";
import { MasterControlGraphPage } from "./pages/MasterControlGraphPage";
import { StationControlPage } from "./pages/StationControlPage";
import { BlockSectionBoardPage } from "./pages/BlockSectionBoardPage";
import { CrossingsPage } from "./pages/CrossingsPage";
import { RestrictionsPage } from "./pages/RestrictionsPage";
import { IncidentsPage } from "./pages/IncidentsPage";
import { HandoverPage } from "./pages/HandoverPage";
import { TrainsPage } from "./pages/Trains";
import { NetworkPage } from "./pages/Network";
import { ConflictsPage } from "./pages/Conflicts";
import { RecommendationsPage } from "./pages/Recommendations";
import { RecommendationDetailPage } from "./pages/RecommendationDetail";
import { DisruptionsPage } from "./pages/Disruptions";
import { WhatIfPage } from "./pages/WhatIf";
import { AnalyticsPage } from "./pages/Analytics";
import { AuditPage } from "./pages/Audit";
import { SpecificationsPage } from "./pages/Specifications";

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
        <Route
          path="graph"
          element={
            <RequireRole roles={["SECTION_MASTER"]}>
              <MasterControlGraphPage />
            </RequireRole>
          }
        />
        <Route path="stations" element={<StationControlPage />} />
        <Route path="blocks" element={<BlockSectionBoardPage />} />
        <Route path="trains" element={<TrainsPage />} />
        <Route path="crossings" element={<CrossingsPage />} />
        <Route path="conflicts" element={<ConflictsPage />} />
        <Route path="recommendations" element={<RecommendationsPage />} />
        <Route path="recommendations/:recommendationId" element={<RecommendationDetailPage />} />
        <Route path="restrictions" element={<RestrictionsPage />} />
        <Route
          path="incidents"
          element={
            <RequireRole roles={["SECTION_MASTER"]}>
              <IncidentsPage />
            </RequireRole>
          }
        />
        <Route
          path="disruptions"
          element={
            <RequireRole roles={["SECTION_MASTER"]}>
              <DisruptionsPage />
            </RequireRole>
          }
        />
        <Route path="network" element={<NetworkPage />} />
        <Route path="what-if" element={<WhatIfPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route
          path="handover"
          element={
            <RequireRole roles={["SECTION_MASTER"]}>
              <HandoverPage />
            </RequireRole>
          }
        />
        <Route path="specifications" element={<SpecificationsPage />} />
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
