import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import { useAuth } from "./auth";
import type { Scenario, SimulationSummary } from "./types";

const SELECTED_KEY = "railgorithm.simulation";

interface SimulationContextValue {
  simulations: SimulationSummary[];
  selectedId: string | null;
  selected: SimulationSummary | null;
  scenarios: Scenario[];
  loading: boolean;
  error: string | null;
  revision: number;
  select: (id: string) => void;
  refresh: () => Promise<void>;
  create: (scenarioKey: string, seed?: number) => Promise<void>;
}

const SimulationContext = createContext<SimulationContextValue | undefined>(
  undefined,
);

export function SimulationProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [simulations, setSimulations] = useState<SimulationSummary[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(
    localStorage.getItem(SELECTED_KEY),
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const [simulationResponse, scenarioResponse] = await Promise.all([
        api.simulations(),
        api.scenarios(),
      ]);
      setSimulations(simulationResponse.simulations);
      setScenarios(scenarioResponse.scenarios);
      setSelectedId((current) => {
        if (current && simulationResponse.simulations.some((item) => item.id === current))
          return current;
        return simulationResponse.simulations[0]?.id ?? null;
      });
      setRevision((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load simulations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    void refresh();
  }, [user, refresh]);

  useEffect(() => {
    if (selectedId) localStorage.setItem(SELECTED_KEY, selectedId);
  }, [selectedId]);

  const select = useCallback((id: string) => setSelectedId(id), []);

  const create = useCallback(
    async (scenarioKey: string, seed?: number) => {
      const created = await api.createSimulation(scenarioKey, seed);
      await refresh();
      setSelectedId(created.id);
    },
    [refresh],
  );

  const selected = useMemo(
    () => simulations.find((item) => item.id === selectedId) ?? null,
    [simulations, selectedId],
  );

  const value = useMemo(
    () => ({
      simulations,
      selectedId,
      selected,
      scenarios,
      loading,
      error,
      revision,
      select,
      refresh,
      create,
    }),
    [simulations, selectedId, selected, scenarios, loading, error, revision, select, refresh, create],
  );

  return (
    <SimulationContext.Provider value={value}>
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation(): SimulationContextValue {
  const context = useContext(SimulationContext);
  if (!context)
    throw new Error("useSimulation must be used inside SimulationProvider");
  return context;
}
