import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { FeedHealthBanner } from "./FeedHealthBanner";
import type { FeedHealthMetrics } from "../types";

const mockFeeds: FeedHealthMetrics[] = [
  {
    feed_id: "feed-telemetry-primary",
    feed_name: "Northern Corridor Live Telemetry API",
    status: "HEALTHY",
    connected: true,
    last_heartbeat_at: "2026-03-01T10:15:30Z",
    freshness_seconds: 4.2,
    is_stale: false,
    events_received_total: 4200,
    events_valid_total: 4195,
    duplicates_detected_total: 12,
    sequence_gaps_total: 0,
    contradictions_detected_total: 0,
    mean_ingestion_latency_ms: 0.05,
    error_rate_pct: 0.12,
    reconnection_attempts: 0,
    circuit_breaker_open: false,
    mode: "AUTHORIZED_PARTNER_API",
    stale_threshold_seconds: 30,
    degraded_threshold_seconds: 15,
  },
];

describe("FeedHealthBanner", () => {
  beforeEach(() => {
    vi.spyOn(api, "feedStatus").mockResolvedValue(mockFeeds);
    vi.spyOn(api, "reconnectFeed").mockResolvedValue({
      success: true,
      status: "reconnected",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the feed health pill with status and freshness", async () => {
    render(<FeedHealthBanner />);
    await waitFor(() => {
      expect(screen.getByText(/FEED: HEALTHY \(4\.2s\)/i)).toBeInTheDocument();
    });
  });

  it("renders stale warning banner when feed is marked stale", async () => {
    const staleFeeds: FeedHealthMetrics[] = [
      {
        ...mockFeeds[0],
        status: "STALE",
        freshness_seconds: 45.0,
        is_stale: true,
      },
    ];
    vi.spyOn(api, "feedStatus").mockResolvedValue(staleFeeds);

    render(<FeedHealthBanner />);
    await waitFor(() => {
      expect(screen.getByText(/FEED STALE:/i)).toBeInTheDocument();
      expect(screen.getByText(/45 seconds ago/i)).toBeInTheDocument();
    });
  });

  it("opens modal on clicking pill and displays metrics", async () => {
    render(<FeedHealthBanner />);
    await waitFor(() => {
      expect(screen.getByText(/FEED: HEALTHY/i)).toBeInTheDocument();
    });

    const button = screen.getByRole("button", { name: /FEED: HEALTHY/i });
    fireEvent.click(button);

    expect(screen.getByText(/Feed Health Telemetry — Northern Corridor Live Telemetry API/i)).toBeInTheDocument();
    expect(screen.getByText(/AUTHORIZED PARTNER API/i)).toBeInTheDocument();
    expect(screen.getByText("4200")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Reconnect Feed \(Reset Circuit Breaker\)/i })).toBeInTheDocument();
  });

  it("triggers reconnect action when clicking reconnect button", async () => {
    render(<FeedHealthBanner />);
    await waitFor(() => {
      expect(screen.getByText(/FEED: HEALTHY/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /FEED: HEALTHY/i }));
    const reconnectBtn = screen.getByRole("button", { name: /Reconnect Feed \(Reset Circuit Breaker\)/i });
    fireEvent.click(reconnectBtn);

    await waitFor(() => {
      expect(api.reconnectFeed).toHaveBeenCalledWith("feed-telemetry-primary");
    });
  });
});
