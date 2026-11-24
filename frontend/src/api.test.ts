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
});
