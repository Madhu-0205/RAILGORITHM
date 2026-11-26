import React, { useMemo, useState } from "react";
import type { Train } from "../types";
import { Badge } from "./ui";

export interface TrainMovementLedgerProps {
  trains?: Train[];
  stations?: any[];
  onSelectTrain?: (trainId: string) => void;
  selectedTrainId?: string | null;
}

export function TrainMovementLedger({
  trains = [],
  stations = [],
  onSelectTrain,
  selectedTrainId,
}: TrainMovementLedgerProps) {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedTrainId, setExpandedTrainId] = useState<string | null>(null);

  // Categorize and enrich trains
  const enrichedTrains = useMemo(() => {
    return trains.map((t) => {
      const isRunning = t.status === "RUNNING";
      const isAtStation = Boolean(t.station_id) || t.status === "AT_STATION";
      const isWaiting = Boolean(t.waiting_reason) || t.status === "WAITING" || t.total_wait_min > 0;
      const delay = t.projected_delay_min || t.delay_min || 0;
      const isDelayed = delay > 0;
      const isStale = t.waiting_reason?.includes("stale") || false;

      let locationLabel = "Pending Departure";
      if (t.station_id) {
        locationLabel = `At Station ${t.station_id}${t.platform ? ` (PF ${t.platform})` : ""}`;
      } else if (t.block_id) {
        locationLabel = `In Block ${t.block_id}${t.section_id ? ` (${t.section_id})` : ""}`;
      } else if (t.status === "COMPLETED") {
        locationLabel = `Terminated at ${t.destination}`;
      }

      return {
        train: t,
        isRunning,
        isAtStation,
        isWaiting,
        isDelayed,
        isStale,
        delay,
        locationLabel,
      };
    });
  }, [trains]);

  // Filtering
  const filteredTrains = useMemo(() => {
    return enrichedTrains.filter(({ train, isRunning, isAtStation, isWaiting, isDelayed, isStale }) => {
      // Status filter
      if (statusFilter === "RUNNING" && !isRunning) return false;
      if (statusFilter === "AT_STATION" && !isAtStation) return false;
      if (statusFilter === "WAITING" && !isWaiting) return false;
      if (statusFilter === "DELAYED" && !isDelayed) return false;
      if (statusFilter === "STALE" && !isStale) return false;

      // Category filter
      if (categoryFilter !== "ALL" && train.train_type !== categoryFilter) return false;

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
  }, [enrichedTrains, statusFilter, categoryFilter, searchQuery]);

  const activeTrain = trains.find((t) => t.id === (expandedTrainId || selectedTrainId));

  const handleRowClick = (trainId: string) => {
    setExpandedTrainId((prev) => (prev === trainId ? null : trainId));
    if (onSelectTrain) onSelectTrain(trainId);
  };

  const runningCount = enrichedTrains.filter((t) => t.isRunning).length;
  const atStationCount = enrichedTrains.filter((t) => t.isAtStation).length;
  const waitingCount = enrichedTrains.filter((t) => t.isWaiting).length;
  const delayedCount = enrichedTrains.filter((t) => t.isDelayed).length;

  return (
    <div className="train-movement-ledger-card stack" style={{ gap: "14px" }}>
      {/* Header Bar */}
      <div
        className="flex-row justify-between items-center flex-wrap gap-2"
        style={{
          background: "#F8FAFC",
          padding: "10px 16px",
          borderRadius: "8px",
          border: "1px solid #E2E8F0",
        }}
      >
        <div className="flex-row items-center gap-3">
          <strong style={{ fontSize: "1rem" }}>Section Train Movement & Regulation Ledger</strong>
          <span className="small text-muted">
            ({enrichedTrains.length} Monitored Movements across territory)
          </span>
        </div>

        {/* Counts summary */}
        <div className="flex-row items-center gap-3 small">
          <span>Running: <strong>{runningCount}</strong></span>
          <span>At Stations: <strong>{atStationCount}</strong></span>
          {waitingCount > 0 && <span style={{ color: "#D97706" }}>Waiting: <strong>{waitingCount}</strong></span>}
          {delayedCount > 0 && <span style={{ color: "#DC2626" }}>Delayed: <strong>{delayedCount}</strong></span>}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex-row justify-between items-center flex-wrap gap-2">
        <div className="button-group" role="group" aria-label="Train status filter">
          <button
            type="button"
            className={`button button-small ${statusFilter === "ALL" ? "button-primary" : "button-ghost"}`}
            onClick={() => setStatusFilter("ALL")}
          >
            All ({enrichedTrains.length})
          </button>
          <button
            type="button"
            className={`button button-small ${statusFilter === "RUNNING" ? "button-primary" : "button-ghost"}`}
            onClick={() => setStatusFilter("RUNNING")}
          >
            Running ({runningCount})
          </button>
          <button
            type="button"
            className={`button button-small ${statusFilter === "AT_STATION" ? "button-primary" : "button-ghost"}`}
            onClick={() => setStatusFilter("AT_STATION")}
          >
            At Station ({atStationCount})
          </button>
          <button
            type="button"
            className={`button button-small ${statusFilter === "DELAYED" ? "button-primary" : "button-ghost"}`}
            onClick={() => setStatusFilter("DELAYED")}
          >
            Delayed ({delayedCount})
          </button>
        </div>

        <div className="flex-row items-center gap-2">
          <select
            className="input input-small"
            style={{ width: "auto" }}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            aria-label="Filter by category"
          >
            <option value="ALL">All Categories</option>
            <option value="EXPRESS">Express</option>
            <option value="PASSENGER">Passenger</option>
            <option value="MEMU">MEMU</option>
            <option value="FREIGHT">Freight</option>
          </select>

          <input
            type="search"
            placeholder="Search train no, name, station..."
            className="input input-small"
            style={{ maxWidth: "240px" }}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search trains in ledger"
          />

          {(statusFilter !== "ALL" || categoryFilter !== "ALL" || searchQuery) && (
            <button
              type="button"
              className="button button-small button-ghost"
              onClick={() => {
                setStatusFilter("ALL");
                setCategoryFilter("ALL");
                setSearchQuery("");
              }}
              title="Reset all filters"
            >
              ↺ Reset
            </button>
          )}
        </div>
      </div>

      {/* Main Table */}
      <div className="table-wrapper" tabIndex={0} role="region" aria-label="Section train movement ledger table">
        <table className="table">
          <thead>
            <tr>
              <th>Train No & Name</th>
              <th>Category</th>
              <th>Direction</th>
              <th>Route</th>
              <th>Last Confirmed Location</th>
              <th>Timings</th>
              <th>Delay</th>
              <th>Status</th>
              <th>Data Quality</th>
            </tr>
          </thead>
          <tbody>
            {filteredTrains.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: "center", padding: "24px", color: "#64748B" }}>
                  No trains match current filters.
                </td>
              </tr>
            ) : (
              filteredTrains.map(({ train, delay, locationLabel, isDelayed }) => {
                const isSelected = selectedTrainId === train.id || expandedTrainId === train.id;

                return (
                  <React.Fragment key={train.id}>
                    <tr
                      className={isSelected ? "row-selected" : undefined}
                      style={{ cursor: "pointer" }}
                      onClick={() => handleRowClick(train.id)}
                    >
                      {/* Train */}
                      <td>
                        <strong>{train.name}</strong>
                        <span className="mono small text-muted d-block">
                          #{train.id}
                        </span>
                      </td>

                      {/* Category & Priority */}
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

                      {/* Location */}
                      <td>
                        <strong>{locationLabel}</strong>
                        {train.next_station && (
                          <span className="small text-muted d-block">
                            Next: {train.next_station}
                          </span>
                        )}
                      </td>

                      {/* Timings */}
                      <td>
                        <div className="small mono">
                          <span>Dep: {train.scheduled_departure || "—"}</span>
                          {train.scheduled_arrival_next && (
                            <span className="text-muted d-block">
                              Next Arr: {train.scheduled_arrival_next}
                            </span>
                          )}
                        </div>
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

                      {/* Status */}
                      <td>
                        <Badge
                          tone={
                            train.status === "RUNNING"
                              ? "good"
                              : train.status === "AT_STATION"
                              ? "default"
                              : "watch"
                          }
                        >
                          {train.status}
                        </Badge>
                      </td>

                      {/* Data Quality */}
                      <td>
                        <span className="badge badge-default" style={{ fontSize: "0.7rem" }}>
                          MEASURED
                        </span>
                      </td>
                    </tr>

                    {/* Expandable Timeline Row */}
                    {expandedTrainId === train.id && (
                      <tr>
                        <td
                          colSpan={9}
                          style={{
                            background: "#F8FAFC",
                            padding: "16px 20px",
                            borderBottom: "2px solid #E2E8F0",
                          }}
                        >
                          <div className="stack gap-2">
                            <div className="flex-row justify-between items-center">
                              <strong style={{ fontSize: "0.9rem", color: "#1E3A8A" }}>
                                Movement Progress & Station Milestones for #{train.id} ({train.name})
                              </strong>
                              <span className="small text-muted">
                                Waiting Reason: {train.waiting_reason || "None (Clear Run)"}
                              </span>
                            </div>

                            {/* Milestone Pills */}
                            <div className="flex-row items-center gap-2 flex-wrap">
                              {(train.route || ["NDL", "KRN", "MLG", "SRP", "VSN"]).map((stCode, idx, arr) => {
                                const isCurrent = train.station_id === stCode;
                                const isPassed =
                                  train.route &&
                                  train.station_id &&
                                  train.route.indexOf(stCode) < train.route.indexOf(train.station_id);

                                return (
                                  <div
                                    key={stCode}
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: "6px",
                                    }}
                                  >
                                    <div
                                      style={{
                                        background: isCurrent ? "#2563EB" : isPassed ? "#16A34A" : "#FFFFFF",
                                        color: isCurrent || isPassed ? "#FFFFFF" : "#475569",
                                        border: `1px solid ${isCurrent ? "#1D4ED8" : isPassed ? "#15803D" : "#CBD5E1"}`,
                                        padding: "6px 12px",
                                        borderRadius: "6px",
                                        fontSize: "0.8rem",
                                        fontWeight: 600,
                                      }}
                                    >
                                      <span>{stCode}</span>
                                      {isCurrent && <span style={{ marginLeft: "4px" }}>🚆</span>}
                                    </div>
                                    {idx < arr.length - 1 && (
                                      <span style={{ color: "#94A3B8", fontWeight: 700 }}>→</span>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
