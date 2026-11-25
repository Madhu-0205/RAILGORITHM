import React, { useMemo, useState } from "react";
import type { Train } from "../types";
import { Badge } from "./ui";

export interface StationTrainBoardProps {
  stationId: string;
  stationName: string;
  trains: Train[];
  onSelectTrain?: (trainId: string) => void;
  selectedTrainId?: string;
}

export function StationTrainBoard({
  stationId,
  stationName,
  trains,
  onSelectTrain,
  selectedTrainId,
}: StationTrainBoardProps) {
  const [statusFilter, setStatusFilter] = useState<"ALL" | "APPROACHING" | "BERTHED" | "DEPARTED" | "DELAYED">("ALL");
  const [directionFilter, setDirectionFilter] = useState<"ALL" | "UP" | "DOWN">("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Categorize trains relative to this station
  const stationTrains = useMemo(() => {
    return trains.map((t) => {
      const isAtStation = t.station_id === stationId;
      const isApproaching = t.next_station === stationId && !isAtStation;
      const isDeparted =
        t.status === "COMPLETED" ||
        (t.route &&
          t.route.includes(stationId) &&
          !isAtStation &&
          !isApproaching &&
          t.route.indexOf(stationId) < (t.station_id ? t.route.indexOf(t.station_id) : 99));

      const delay = t.projected_delay_min || t.delay_min || 0;
      const isDelayed = delay > 0;

      let opStatus: "BERTHED" | "APPROACHING" | "DEPARTED" | "EN_ROUTE" = "EN_ROUTE";
      if (isAtStation) opStatus = "BERTHED";
      else if (isApproaching) opStatus = "APPROACHING";
      else if (isDeparted) opStatus = "DEPARTED";

      return {
        train: t,
        opStatus,
        isAtStation,
        isApproaching,
        isDeparted,
        isDelayed,
        delay,
      };
    });
  }, [trains, stationId]);

  // Filtering
  const filteredTrains = useMemo(() => {
    return stationTrains.filter(({ train, opStatus, isDelayed }) => {
      // Status filter
      if (statusFilter === "APPROACHING" && opStatus !== "APPROACHING") return false;
      if (statusFilter === "BERTHED" && opStatus !== "BERTHED") return false;
      if (statusFilter === "DEPARTED" && opStatus !== "DEPARTED") return false;
      if (statusFilter === "DELAYED" && !isDelayed) return false;

      // Direction filter
      if (directionFilter !== "ALL" && train.direction !== directionFilter) return false;

      // Search query
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        train.id.toLowerCase().includes(q) ||
        train.name.toLowerCase().includes(q) ||
        train.origin.toLowerCase().includes(q) ||
        train.destination.toLowerCase().includes(q)
      );
    });
  }, [stationTrains, statusFilter, directionFilter, searchQuery]);

  // Counts for tabs
  const berthedCount = stationTrains.filter((t) => t.opStatus === "BERTHED").length;
  const approachingCount = stationTrains.filter((t) => t.opStatus === "APPROACHING").length;
  const delayedCount = stationTrains.filter((t) => t.isDelayed).length;

  return (
    <div className="station-train-board-card stack" style={{ gap: "16px" }}>
      {/* Board Header styled like Station Electronic Display */}
      <div
        className="train-board-header flex-row justify-between items-center flex-wrap gap-3"
        style={{
          background: "#0F172A", // Railway board navy/slate
          color: "#FFFFFF",
          padding: "14px 20px",
          borderRadius: "8px",
          border: "1px solid #1E293B",
          boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        }}
      >
        <div className="flex-row items-center gap-3">
          <span
            style={{
              background: "#F59E0B",
              color: "#0F172A",
              padding: "4px 8px",
              borderRadius: "4px",
              fontWeight: 800,
              fontSize: "0.85rem",
              fontFamily: "monospace",
            }}
          >
            {stationId}
          </span>
          <div>
            <h3 style={{ margin: 0, fontSize: "1.1rem", letterSpacing: "0.02em" }}>
              {stationName} Operational Train Board
            </h3>
            <span style={{ fontSize: "0.8rem", color: "#94A3B8" }}>
              National Train Enquiry & Station Master Movements Ledger
            </span>
          </div>
        </div>

        {/* Live Status Indicators */}
        <div className="flex-row items-center gap-3">
          <div className="flex-row items-center gap-1 small" style={{ color: "#93C5FD" }}>
            <span>Berthed: <strong>{berthedCount}</strong></span>
          </div>
          <div className="flex-row items-center gap-1 small" style={{ color: "#FCD34D" }}>
            <span>Approaching: <strong>{approachingCount}</strong></span>
          </div>
          <div className="flex-row items-center gap-1 small" style={{ color: "#FCA5A5" }}>
            <span>Delayed: <strong>{delayedCount}</strong></span>
          </div>
        </div>
      </div>

      {/* Tabs and Search Bar */}
      <div className="flex-row justify-between items-center flex-wrap gap-3">
        {/* Status Filter Tabs */}
        <div className="button-group" role="group" aria-label="Train status tabs">
          <button
            type="button"
            className={`button button-small ${statusFilter === "ALL" ? "button-primary" : "button-ghost"}`}
            onClick={() => setStatusFilter("ALL")}
          >
            All Trains ({stationTrains.length})
          </button>
          <button
            type="button"
            className={`button button-small ${statusFilter === "APPROACHING" ? "button-primary" : "button-ghost"}`}
            onClick={() => setStatusFilter("APPROACHING")}
          >
            Approaching ({approachingCount})
          </button>
          <button
            type="button"
            className={`button button-small ${statusFilter === "BERTHED" ? "button-primary" : "button-ghost"}`}
            onClick={() => setStatusFilter("BERTHED")}
          >
            At Platform ({berthedCount})
          </button>
          <button
            type="button"
            className={`button button-small ${statusFilter === "DELAYED" ? "button-primary" : "button-ghost"}`}
            onClick={() => setStatusFilter("DELAYED")}
          >
            Delayed ({delayedCount})
          </button>
        </div>

        {/* Direction & Search */}
        <div className="flex-row items-center gap-2">
          <select
            className="input input-small"
            style={{ width: "auto" }}
            value={directionFilter}
            onChange={(e) => setDirectionFilter(e.target.value as "ALL" | "UP" | "DOWN")}
            aria-label="Filter by train direction"
          >
            <option value="ALL">All Directions</option>
            <option value="UP">UP Only</option>
            <option value="DOWN">DOWN Only</option>
          </select>

          <input
            type="search"
            placeholder="Search train no, name..."
            className="input input-small"
            style={{ maxWidth: "220px" }}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search trains by number or name"
          />
        </div>
      </div>

      {/* Train Board Table */}
      <div className="table-wrapper" tabIndex={0} role="region" aria-label="Station train movement schedule table">
        <table className="table">
          <thead>
            <tr>
              <th>Train No & Name</th>
              <th>Category</th>
              <th>Direction</th>
              <th>Route</th>
              <th>Platform</th>
              <th>Scheduled Time</th>
              <th>Expected / Actual</th>
              <th>Delay Status</th>
              <th>Operating Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredTrains.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: "center", padding: "24px", color: "#64748B" }}>
                  No train movements matching current filters.
                </td>
              </tr>
            ) : (
              filteredTrains.map(({ train, opStatus, delay }) => {
                const isSelected = selectedTrainId === train.id;

                const statusTone =
                  opStatus === "BERTHED"
                    ? "default"
                    : opStatus === "APPROACHING"
                    ? "watch"
                    : opStatus === "DEPARTED"
                    ? "muted"
                    : "good";

                const isDelayed = delay > 0;

                return (
                  <tr
                    key={train.id}
                    className={isSelected ? "row-selected" : undefined}
                    style={{ cursor: onSelectTrain ? "pointer" : "default" }}
                    onClick={() => onSelectTrain && onSelectTrain(train.id)}
                  >
                    {/* Train Info */}
                    <td>
                      <strong>{train.name}</strong>
                      <span className="mono small text-muted d-block">
                        #{train.id}
                      </span>
                    </td>

                    {/* Category / Priority */}
                    <td>
                      <Badge tone="muted">
                        {train.train_type} (P{train.priority})
                      </Badge>
                    </td>

                    {/* Direction */}
                    <td>
                      <Badge tone="muted">{train.direction}</Badge>
                    </td>

                    {/* Route */}
                    <td>
                      <span className="mono small">
                        {train.origin} → {train.destination}
                      </span>
                    </td>

                    {/* Platform */}
                    <td>
                      {train.platform ? (
                        <span
                          style={{
                            background: "#0F172A",
                            color: "#FFFFFF",
                            padding: "3px 8px",
                            borderRadius: "4px",
                            fontWeight: 700,
                            fontFamily: "monospace",
                            fontSize: "0.85rem",
                          }}
                        >
                          PF {train.platform}
                        </span>
                      ) : (
                        <span className="text-muted small">Not berthed</span>
                      )}
                    </td>

                    {/* Scheduled Time */}
                    <td>
                      <span className="mono small">
                        Dep: {train.scheduled_departure || "—"}
                      </span>
                    </td>

                    {/* Expected Time */}
                    <td>
                      <span className="mono small">
                        Next: {train.scheduled_arrival_next || "—"}
                      </span>
                    </td>

                    {/* Delay */}
                    <td>
                      <span
                        className={isDelayed ? "text-bad" : "text-good"}
                        style={{ fontWeight: 600 }}
                      >
                        {isDelayed ? `+${delay} min` : "Right Time"}
                      </span>
                    </td>

                    {/* Status Badge */}
                    <td>
                      <Badge tone={statusTone}>
                        {opStatus}
                      </Badge>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
