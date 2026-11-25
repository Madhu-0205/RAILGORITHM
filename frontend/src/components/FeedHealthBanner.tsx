import { useEffect, useState } from "react";
import { api } from "../api";
import type { FeedHealthMetrics } from "../types";
import { Badge, Modal } from "./ui";

export function FeedHealthBanner() {
  const [feeds, setFeeds] = useState<FeedHealthMetrics[]>([]);
  const [selectedFeed, setSelectedFeed] = useState<FeedHealthMetrics | null>(null);
  const [reconnecting, setReconnecting] = useState(false);

  useEffect(() => {
    let mounted = true;
    const fetchStatus = () => {
      api.feedStatus().then((data) => {
        if (mounted) setFeeds(data);
      }).catch(() => {
        // Feed status fallback
      });
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 8000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (feeds.length === 0) return null;
  const primary = feeds[0];

  const tone =
    primary.status === "HEALTHY"
      ? "good"
      : primary.status === "DEGRADED"
      ? "watch"
      : "bad";

  async function handleReconnect(feedId: string) {
    setReconnecting(true);
    try {
      await api.reconnectFeed(feedId);
      const updated = await api.feedStatus();
      setFeeds(updated);
      setSelectedFeed(updated.find((f) => f.feed_id === feedId) ?? null);
    } catch {
      // Reconnect handled gracefully
    } finally {
      setReconnecting(false);
    }
  }

  return (
    <>
      <div className="feed-health-pill-container">
        <button
          type="button"
          className="feed-health-button"
          onClick={() => setSelectedFeed(primary)}
          title="Click to inspect real-time railway data feed health"
        >
          <span className={`status-dot dot-${primary.status.toLowerCase()}`} />
          <span className="feed-status-text">
            FEED: {primary.status} ({primary.freshness_seconds}s)
          </span>
        </button>
      </div>

      {primary.is_stale && (
        <div className="banner banner-warning" role="alert">
          <strong>FEED STALE:</strong> Live railway telemetry was last received{" "}
          {primary.freshness_seconds} seconds ago. Scheduling recommendations continue
          using deterministic simulation models with explicit stale notices.
        </div>
      )}

      {selectedFeed && (
        <Modal
          title={`Feed Health Telemetry — ${selectedFeed.feed_name}`}
          onClose={() => setSelectedFeed(null)}
        >
          <div className="stack">
            <div className="grid-2">
              <div>
                <strong>Feed ID</strong>
                <p className="muted">{selectedFeed.feed_id}</p>
              </div>
              <div>
                <strong>Status</strong>
                <p>
                  <Badge tone={tone}>{selectedFeed.status}</Badge>
                </p>
              </div>
              <div>
                <strong>Data Mode</strong>
                <p className="muted">{selectedFeed.mode.replace(/_/g, " ")}</p>
              </div>
              <div>
                <strong>Freshness Age</strong>
                <p>{selectedFeed.freshness_seconds} seconds</p>
              </div>
            </div>

            <div className="kpi-grid">
              <div className="metric-box">
                <small className="muted">Total Events</small>
                <strong>{selectedFeed.events_received_total}</strong>
              </div>
              <div className="metric-box">
                <small className="muted">Valid Events</small>
                <strong>{selectedFeed.events_valid_total}</strong>
              </div>
              <div className="metric-box">
                <small className="muted">Duplicates Filtered</small>
                <strong>{selectedFeed.duplicates_detected_total}</strong>
              </div>
              <div className="metric-box">
                <small className="muted">Sequence Gaps</small>
                <strong>{selectedFeed.sequence_gaps_total}</strong>
              </div>
              <div className="metric-box">
                <small className="muted">Contradictions Blocked</small>
                <strong>{selectedFeed.contradictions_detected_total}</strong>
              </div>
              <div className="metric-box">
                <small className="muted">Mean Ingestion Latency</small>
                <strong>{selectedFeed.mean_ingestion_latency_ms} ms</strong>
              </div>
            </div>

            <div className="dialog-actions">
              <button
                type="button"
                className="button button-small button-primary"
                disabled={reconnecting}
                onClick={() => handleReconnect(selectedFeed.feed_id)}
              >
                {reconnecting ? "Reconnecting..." : "Reconnect Feed (Reset Circuit Breaker)"}
              </button>
              <button
                type="button"
                className="button button-small button-ghost"
                onClick={() => setSelectedFeed(null)}
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
