import { useMemo } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import type { Network, Section, Station } from "../types";
import { EmptyState, ErrorBanner, Panel, Spinner } from "../components/ui";
import { ConflictRegulationWorkspace } from "../components/ConflictRegulationWorkspace";

const DEFAULT_STATIONS: Station[] = [
  { id: "NDL", name: "Nandpur", code: "NDL", platforms: ["P1", "P2"], x: 0, is_junction: false },
  { id: "KRN", name: "Karanpur", code: "KRN", platforms: ["P1", "P2"], x: 25, is_junction: false },
  { id: "MLG", name: "Malgaon Junction", code: "MLG", platforms: ["P1", "P2", "P3"], x: 50, is_junction: true },
  { id: "SRP", name: "Suryapur", code: "SRP", platforms: ["P1", "P2"], x: 75, is_junction: false },
  { id: "VSN", name: "Vasanthpur", code: "VSN", platforms: ["P1", "P2"], x: 100, is_junction: false },
];

export function CrossingsPage() {
  const { selectedId, revision } = useSimulation();

  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.dashboard(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const { data: networkData } = useAsync<{ network: Network } | null>(
    () => (selectedId ? api.network(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const { data: sectionKpis } = useAsync(
    () => (selectedId ? api.sectionKpis(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const corridorStations = networkData?.network.stations || DEFAULT_STATIONS;
  const corridorTrains = data?.trains || [];
  const corridorConflicts = sectionKpis?.active_conflicts || data?.conflicts || [];
  const pendingDecisions = sectionKpis?.pending_decisions || [];

  const singleLineMeets = useMemo(() => {
    return corridorConflicts.filter(
      (c) =>
        c.type === "SINGLE_LINE_CROSSING" ||
        c.type === "CROSSING_CONFLICT" ||
        c.type === "OVERTAKING_CONFLICT" ||
        c.type === "HEADWAY",
    );
  }, [corridorConflicts]);

  if (!selectedId) {
    return (
      <EmptyState
        title="No simulation selected"
        description="Select an active simulation to manage crossings and precedence."
      />
    );
  }

  if (loading && !data) return <Spinner label="Loading Crossings & Precedence..." />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="stack">
      {/* Workspace Header */}
      <div className="page-heading">
        <div>
          <div className="flex-row gap-2 items-center">
            <h1>Crossings & Precedence Regulation Desk</h1>
            <span className="badge badge-accent">SINGLE-LINE MEETS & OVERTAKINGS</span>
          </div>
          <p className="muted">
            Indian Railways Traffic Facility Rules · Single-line loop holding, train priority enforcement, and crossing coordination
          </p>
        </div>
        <div className="heading-badges flex-row gap-2 items-center">
          <Link to="/" className="button button-small button-ghost">
            ← Back to Overview
          </Link>
          <span className="badge badge-watch">Sim Time: {data.simulation.sim_time} IST</span>
        </div>
      </div>

      {/* Meet & Priority Regulation Overview Banner */}
      <div
        className="flex-row justify-between items-center"
        style={{
          background: "#0F172A",
          color: "#F8FAFC",
          padding: "12px 16px",
          borderRadius: "8px",
          gap: "12px",
          flexWrap: "wrap",
          border: "1px solid #1E293B",
        }}
      >
        <div className="flex-row items-center gap-3">
          <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#38BDF8" }}>
            STATUTORY PRECEDENCE HIERARCHY:
          </span>
          <span className="badge" style={{ background: "#1E293B", color: "#F1F5F9" }}>
            1. Superfast / Mail Express (P1)
          </span>
          <span style={{ color: "#64748B" }}>&gt;</span>
          <span className="badge" style={{ background: "#1E293B", color: "#F1F5F9" }}>
            2. Ordinary Passenger / EMU (P2)
          </span>
          <span style={{ color: "#64748B" }}>&gt;</span>
          <span className="badge" style={{ background: "#1E293B", color: "#F1F5F9" }}>
            3. Through Freight / Container (P3)
          </span>
        </div>
        <div className="flex-row items-center gap-2">
          <span className="badge badge-watch">
            {singleLineMeets.length} Active Crossings / Overtakes
          </span>
        </div>
      </div>

      {/* Main Conflict Regulation Workspace Component */}
      <ConflictRegulationWorkspace
        conflicts={corridorConflicts}
        pendingDecisions={pendingDecisions}
        trains={corridorTrains}
        stations={corridorStations}
      />

      {/* Single-Line Bottlenecks & Loop Capacity Guide */}
      <div className="grid-two">
        <Panel
          title="Section S1: Nandpur (NDL) ⇄ Karanpur (KRN)"
          subtitle="Single-line track (12 min transit time) · Running on Absolute Block token clearance"
        >
          <div className="stack">
            <p className="small">
              <strong>Ruling Gradient / Speed:</strong> 90 km/h · <strong>Minimum Headway:</strong> 4 min
            </p>
            <div className="flex-row gap-2">
              <span className="badge badge-default">NDL: Main (P1) + Loop (P2)</span>
              <span className="badge badge-default">KRN: Main (P1) + Loop (P2)</span>
            </div>
            <p className="small muted">
              Rule: Lower priority train enters loop first and stops clear of fouling mark before line clear is granted to opposing high-priority train.
            </p>
          </div>
        </Panel>

        <Panel
          title="Section S3: Malgaon Junction (MLG) ⇄ Suryapur (SRP)"
          subtitle="Single-line track (14 min transit time) · Critical throat bottleneck"
        >
          <div className="stack">
            <p className="small">
              <strong>Ruling Gradient / Speed:</strong> 90 km/h · <strong>Minimum Headway:</strong> 4 min
            </p>
            <div className="flex-row gap-2">
              <span className="badge badge-default">MLG: P1 + P2 + P3 (Junction)</span>
              <span className="badge badge-default">SRP: Main (P1) + Loop (P2)</span>
            </div>
            <p className="small muted">
              Rule: Malgaon diamond crossing moves must clear junction throat before granting line clear on Section S3 to avoid cascading detention.
            </p>
          </div>
        </Panel>
      </div>
    </div>
  );
}
