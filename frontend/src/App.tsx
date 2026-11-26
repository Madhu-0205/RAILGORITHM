import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { StationMasterShell } from "./components/StationMasterShell";
import { SectionControllerShell } from "./components/SectionControllerShell";
import { Spinner } from "./components/ui";
import { LoginPage } from "./pages/Login";
import { StationMasterLoginPage } from "./pages/StationMasterLoginPage";
import { SectionControllerLoginPage } from "./pages/SectionControllerLoginPage";
import { StationMasterWorkspace } from "./pages/StationMasterWorkspace";
import { SectionControllerWorkspace } from "./pages/SectionControllerWorkspace";
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

function RootRedirect() {
  const { user, initialising } = useAuth();
  if (initialising) return <Spinner label="Restoring session" />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "STATION_MASTER") {
    return <Navigate to="/station-master/dashboard" replace />;
  }
  return <Navigate to="/section-controller/dashboard" replace />;
}

function RequireStationMasterAuth({ children }: { children: ReactNode }) {
  const { user, initialising } = useAuth();
  if (initialising) return <Spinner label="Restoring session" />;
  if (!user) return <Navigate to="/login/station-master" replace />;
  if (user.role !== "STATION_MASTER" && user.role !== "ADMIN") {
    return (
      <div style={{ padding: "40px 24px", maxWidth: "600px", margin: "40px auto", textAlign: "center" }}>
        <div className="banner banner-danger" role="alert" style={{ padding: "24px", borderRadius: "8px" }}>
          <h2 style={{ margin: "0 0 12px", color: "#fca5a5" }}>🔒 Access Denied: Station Master Workspace Only</h2>
          <p style={{ color: "#f8fafc", margin: "0 0 16px" }}>
            You are logged in as <strong>{user.display_name}</strong> with role <strong>{user.role}</strong>.
            This workspace is strictly restricted to Station Masters.
          </p>
          <a
            href="/section-controller/dashboard"
            style={{
              display: "inline-block",
              background: "#0284c7",
              color: "#f8fafc",
              padding: "10px 18px",
              borderRadius: "6px",
              textDecoration: "none",
              fontWeight: 700,
            }}
          >
            Go to Section Controller Console →
          </a>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}

function RequireSectionControllerAuth({ children }: { children: ReactNode }) {
  const { user, initialising } = useAuth();
  if (initialising) return <Spinner label="Restoring session" />;
  if (!user) return <Navigate to="/login/section-controller" replace />;
  const isSectionRole =
    user.role === "SECTION_CONTROLLER" || user.role === "SECTION_MASTER" || user.role === "ADMIN";
  if (!isSectionRole) {
    return (
      <div style={{ padding: "40px 24px", maxWidth: "600px", margin: "40px auto", textAlign: "center" }}>
        <div className="banner banner-danger" role="alert" style={{ padding: "24px", borderRadius: "8px" }}>
          <h2 style={{ margin: "0 0 12px", color: "#fca5a5" }}>🔒 Access Denied: Section Controller Workspace Only</h2>
          <p style={{ color: "#f8fafc", margin: "0 0 16px" }}>
            You are logged in as <strong>{user.display_name}</strong> with role <strong>{user.role}</strong>.
            This workspace is strictly restricted to Section Controllers.
          </p>
          <a
            href="/station-master/dashboard"
            style={{
              display: "inline-block",
              background: "#f59e0b",
              color: "#0f172a",
              padding: "10px 18px",
              borderRadius: "6px",
              textDecoration: "none",
              fontWeight: 700,
            }}
          >
            Go to Station Master Console →
          </a>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}

export function App() {
  const { user, initialising } = useAuth();

  return (
    <Routes>
      {/* 1. SEPARATE AUTHENTICATION ENTRY POINTS */}
      <Route
        path="/login"
        element={
          initialising ? (
            <Spinner label="Restoring session" />
          ) : user ? (
            <RootRedirect />
          ) : (
            <LoginPage />
          )
        }
      />
      <Route
        path="/login/station-master"
        element={
          initialising ? (
            <Spinner label="Restoring session" />
          ) : user?.role === "STATION_MASTER" ? (
            <Navigate to="/station-master/dashboard" replace />
          ) : (
            <StationMasterLoginPage />
          )
        }
      />
      <Route
        path="/station-master/login"
        element={<Navigate to="/login/station-master" replace />}
      />
      <Route
        path="/login/section-controller"
        element={
          initialising ? (
            <Spinner label="Restoring session" />
          ) : (user?.role === "SECTION_CONTROLLER" || user?.role === "SECTION_MASTER") ? (
            <Navigate to="/section-controller/dashboard" replace />
          ) : (
            <SectionControllerLoginPage />
          )
        }
      />
      <Route
        path="/section-controller/login"
        element={<Navigate to="/login/section-controller" replace />}
      />

      {/* 2. DEDICATED STATION MASTER APPLICATION SHELL & WORKSPACES */}
      <Route
        path="/station-master"
        element={
          <RequireStationMasterAuth>
            <StationMasterShell />
          </RequireStationMasterAuth>
        }
      >
        <Route index element={<StationMasterWorkspace />} />
        <Route path="dashboard" element={<StationMasterWorkspace />} />
        <Route path="yard" element={<StationMasterWorkspace />} />
        <Route path="trains" element={<TrainsPage />} />
        <Route path="adjacent" element={<StationMasterWorkspace />} />
        <Route path="platforms" element={<StationControlPage />} />
        <Route path="alerts" element={<ConflictsPage />} />
        <Route path="rules" element={<SpecificationsPage />} />
      </Route>

      {/* 3. DEDICATED SECTION CONTROLLER APPLICATION SHELL & WORKSPACES */}
      <Route
        path="/section-controller"
        element={
          <RequireSectionControllerAuth>
            <SectionControllerShell />
          </RequireSectionControllerAuth>
        }
      >
        <Route index element={<SectionControllerWorkspace />} />
        <Route path="dashboard" element={<SectionControllerWorkspace />} />
        <Route path="graph" element={<MasterControlGraphPage />} />
        <Route path="topology" element={<SectionControllerWorkspace />} />
        <Route path="blocks" element={<BlockSectionBoardPage />} />
        <Route path="trains" element={<TrainsPage />} />
        <Route path="crossings" element={<CrossingsPage />} />
        <Route path="junctions" element={<SectionControllerWorkspace />} />
        <Route path="conflicts" element={<ConflictsPage />} />
        <Route path="recommendations" element={<RecommendationsPage />} />
        <Route path="recommendations/:recommendationId" element={<RecommendationDetailPage />} />
        <Route path="restrictions" element={<RestrictionsPage />} />
        <Route path="incidents" element={<IncidentsPage />} />
        <Route path="disruptions" element={<DisruptionsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="handover" element={<HandoverPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="rules" element={<SpecificationsPage />} />
      </Route>

      {/* 4. ROOT ROUTE & BACKWARD COMPATIBLE REDIRECTS */}
      <Route path="/" element={<RootRedirect />} />
      <Route path="/dashboard" element={<RootRedirect />} />
      <Route path="/station-yard" element={<Navigate to="/station-master/dashboard" replace />} />
      <Route path="/master-graph" element={<Navigate to="/section-controller/graph" replace />} />
      <Route path="/graph" element={<Navigate to="/section-controller/graph" replace />} />
      <Route path="/blocks" element={<Navigate to="/section-controller/blocks" replace />} />
      <Route path="/crossings" element={<Navigate to="/section-controller/crossings" replace />} />
      <Route path="/handover" element={<Navigate to="/section-controller/handover" replace />} />
      <Route path="/audit" element={<Navigate to="/section-controller/audit" replace />} />
      <Route path="/restrictions" element={<Navigate to="/section-controller/restrictions" replace />} />
      <Route path="/incidents" element={<Navigate to="/section-controller/incidents" replace />} />

      {/* 5. CATCH-ALL */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
