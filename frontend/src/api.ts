import type {
  Analytics,
  AuditEvent,
  Dashboard,
  Decision,
  LoginResponse,
  ModelRecord,
  Network,
  RecommendationDetail,
  RecommendationSummary,
  Scenario,
  SimulationSummary,
  SimulationView,
  Train,
  User,
  WhatIfResult,
  Conflict,
} from "./types";

const BASE = "/api/v1";
const TOKEN_KEY = "railgorithm.token";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((item: { msg?: string }) => item.msg ?? "Invalid input")
          .join("; ");
      }
    } catch {
      // Keep the status-based message when the body is not JSON.
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  login(username: string, password: string) {
    return request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },
  me() {
    return request<User>("/auth/me");
  },
  scenarios() {
    return request<{ scenarios: Scenario[]; label: string; note: string }>(
      "/scenarios",
    );
  },
  simulations() {
    return request<{ simulations: SimulationSummary[]; label: string }>(
      "/simulations",
    );
  },
  createSimulation(scenario_key: string, seed?: number) {
    return request<SimulationView>("/simulations", {
      method: "POST",
      body: JSON.stringify({ scenario_key, seed }),
    });
  },
  simulation(id: string) {
    return request<SimulationView>(`/simulations/${id}`);
  },
  dashboard(id: string) {
    return request<Dashboard>(`/simulations/${id}/dashboard`);
  },
  trains(id: string) {
    return request<{ trains: Train[]; sim_time: string; state_version: number }>(
      `/simulations/${id}/trains`,
    );
  },
  network(id: string) {
    return request<{
      network: Network;
      block_occupancy: SimulationView["block_occupancy"];
      platforms: SimulationView["platforms"];
      closures: SimulationView["closures"];
      platform_outages: SimulationView["platform_outages"];
      sim_time: string;
      state_version: number;
    }>(`/simulations/${id}/network`);
  },
  conflicts(id: string) {
    return request<{
      conflicts: Conflict[];
      total_detected: number;
      scope_filtered: boolean;
      sim_time: number;
      state_version: number;
    }>(`/simulations/${id}/conflicts`);
  },
  recommendations(id: string) {
    return request<{
      recommendations: RecommendationSummary[];
      simulation_id: string;
      state_version: number;
    }>(`/simulations/${id}/recommendations`);
  },
  recommendation(recommendationId: string) {
    return request<RecommendationDetail>(
      `/recommendations/${recommendationId}`,
    );
  },
  generateRecommendation(id: string, parentRecommendationId?: string) {
    return request<RecommendationDetail>(`/simulations/${id}/recommendations`, {
      method: "POST",
      body: JSON.stringify({
        parent_recommendation_id: parentRecommendationId ?? null,
      }),
    });
  },
  decide(
    recommendationId: string,
    payload: {
      action: string;
      rationale: string;
      confirm_apply: boolean;
      modifications?: Record<string, unknown> | null;
    },
  ) {
    return request<{
      decision: Decision;
      recommendation: RecommendationDetail;
      new_recommendation: RecommendationDetail | null;
      simulation_state_version: number;
      note: string;
    }>(`/recommendations/${recommendationId}/decision`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  advance(id: string, minutes: number) {
    return request<SimulationView>(`/simulations/${id}/advance`, {
      method: "POST",
      body: JSON.stringify({ minutes }),
    });
  },
  pause(id: string, paused: boolean) {
    return request<SimulationView>(`/simulations/${id}/pause`, {
      method: "POST",
      body: JSON.stringify({ paused }),
    });
  },
  reset(id: string) {
    return request<SimulationView>(`/simulations/${id}/reset`, {
      method: "POST",
    });
  },
  disruption(
    id: string,
    disruption_type: string,
    payload: Record<string, unknown>,
  ) {
    return request<SimulationView>(`/simulations/${id}/disruptions`, {
      method: "POST",
      body: JSON.stringify({ disruption_type, payload }),
    });
  },
  whatIf(id: string, action: Record<string, unknown>, minutes: number) {
    return request<WhatIfResult>(`/simulations/${id}/what-if`, {
      method: "POST",
      body: JSON.stringify({ action, minutes }),
    });
  },
  analytics(id: string) {
    return request<Analytics>(`/simulations/${id}/analytics`);
  },
  audit(limit = 100) {
    return request<{
      events: AuditEvent[];
      verification: { valid: boolean; events: number; head_hash?: string };
      append_only: boolean;
    }>(`/audit?limit=${limit}`);
  },
  models() {
    return request<{ models: ModelRecord[]; disclaimer: string }>("/models");
  },
};
