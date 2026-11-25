import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, getToken, setToken } from "./api";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("token storage", () => {
  it("stores and clears the token", () => {
    setToken("abc");
    expect(getToken()).toBe("abc");
    setToken(null);
    expect(getToken()).toBeNull();
  });
});

describe("api client", () => {
  it("sends the bearer token and parses JSON", async () => {
    setToken("token-123");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ username: "section.master" }));

    const user = await api.me();

    expect(user.username).toBe("section.master");
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/auth/me");
    expect((options?.headers as Record<string, string>).Authorization).toBe(
      "Bearer token-123",
    );
  });

  it("maps a string error detail to ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "Insufficient role" }, 403),
    );

    await expect(api.audit()).rejects.toMatchObject({
      name: "Error",
      message: "Insufficient role",
      status: 403,
    });
    await expect(api.audit()).rejects.toBeInstanceOf(ApiError);
  });

  it("joins validation error arrays", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        { detail: [{ msg: "field required" }, { msg: "too short" }] },
        422,
      ),
    );

    await expect(
      api.decide("rec-1", { action: "REJECT", rationale: "x", confirm_apply: false }),
    ).rejects.toThrow("field required; too short");
  });

  it("falls back to a status message for non-JSON bodies", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    } as unknown as Response);

    await expect(api.models()).rejects.toThrow("status 500");
  });

  it("fetches feed status and posts reconnect feed", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse([
          {
            feed_id: "feed-1",
            feed_name: "Mock Feed",
            status: "HEALTHY",
            mode: "AUTHORIZED_PARTNER_API",
            freshness_seconds: 1.5,
          },
        ]),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          status: "reconnected",
          feed_id: "feed-1",
          connected: true,
        }),
      );

    const feeds = await api.feedStatus();
    expect(feeds).toHaveLength(1);
    expect(feeds[0].feed_id).toBe("feed-1");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/ingestion/status");

    const rec = await api.reconnectFeed("feed-1");
    expect(rec.status).toBe("reconnected");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/ingestion/feeds/feed-1/reconnect");
  });

  it("fetches station and section kpis", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse({
          station_id: "MLG",
          station_name: "Malgaon Junction",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          time_period: "06:00 - 07:00 IST",
        }),
      );

    const station = await api.stationKpis("sim-1", "MLG");
    expect(station.station_id).toBe("MLG");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/simulations/sim-1/analytics/station-master?station_id=MLG");

    const section = await api.sectionKpis("sim-1");
    expect(section.time_period).toContain("IST");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/simulations/sim-1/analytics/section-controller");
  });
});
