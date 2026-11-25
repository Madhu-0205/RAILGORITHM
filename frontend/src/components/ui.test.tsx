import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  EmptyState,
  EvidenceBadge,
  KpiCard,
  SeverityBadge,
  SyntheticBanner,
} from "./ui";

describe("SyntheticBanner", () => {
  it("states clearly that data is synthetic and no live system is connected", () => {
    render(<SyntheticBanner />);
    const banner = screen.getByRole("note");
    expect(banner).toHaveTextContent(/SYNTHETIC DATA/i);
    expect(banner).toHaveTextContent(/not real Indian Railways data/i);
    expect(banner).toHaveTextContent(/human controller must decide/i);
    expect(banner).toHaveTextContent(/no live railway systems/i);
  });
});

describe("badges", () => {
  it("renders the severity as text", () => {
    render(<SeverityBadge severity="CRITICAL" />);
    expect(screen.getByText("CRITICAL")).toHaveClass("severity-critical");
  });

  it("labels evidence without overclaiming", () => {
    render(<EvidenceBadge status="VALIDATED_WITH_ASSUMPTIONS" />);
    expect(screen.getByText(/validated with stated assumptions/i)).toBeInTheDocument();
  });
});

describe("KpiCard", () => {
  it("shows the unit and hint", () => {
    render(
      <KpiCard label="Average delay" value="7.5" unit=" min" hint="max 12 min" />,
    );
    expect(screen.getByText("Average delay")).toBeInTheDocument();
    expect(screen.getByText("7.5")).toBeInTheDocument();
    expect(screen.getByText("max 12 min")).toBeInTheDocument();
  });

  it("renders reporting period, data source, and data quality indicator when provided", () => {
    render(
      <KpiCard
        label="Schedule Adherence"
        value="85.5"
        unit="%"
        period="Rolling 60m"
        source="Station Arrival Log"
        quality="CALCULATED"
        tooltip="Trains within 5 minutes of scheduled timetable"
      />,
    );
    expect(screen.getByText("Rolling 60m")).toBeInTheDocument();
    expect(screen.getByText(/CALCULATED/i)).toBeInTheDocument();
    expect(screen.getByTitle("Trains within 5 minutes of scheduled timetable")).toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(<EmptyState title="No conflicts" description="Nothing projected." />);
    expect(screen.getByText("No conflicts")).toBeInTheDocument();
    expect(screen.getByText("Nothing projected.")).toBeInTheDocument();
  });
});
