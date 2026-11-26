import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CoordinationAndHandover } from "./CoordinationAndHandover";

describe("CoordinationAndHandover", () => {
  it("renders coordination diary and logs new notes", () => {
    render(
      <CoordinationAndHandover
        territoryName="Northern Section"
        simTime="06:24"
        activeTrainsCount={4}
        delayedTrainsCount={1}
        openConflictsCount={2}
        activeRestrictionsCount={1}
      />
    );

    // Header & tabs
    expect(screen.getByText(/Control Office Coordination & Shift Handover Workspace/i)).toBeDefined();
    expect(screen.getByText(/Coordination Diary/i)).toBeDefined();
    expect(screen.getByText(/Shift Handover Console/i)).toBeDefined();

    // Existing messages
    expect(screen.getByText("MSG-101")).toBeDefined();
    expect(screen.getByText(/Verify line clear granted for Up Mail 12625/i)).toBeDefined();

    // Log a new note
    const input = screen.getByRole("textbox", { name: /Message content/i });
    fireEvent.change(input, { target: { value: "Speed test completed on Section S2" } });
    fireEvent.click(screen.getByRole("button", { name: /Log Note/i }));

    expect(screen.getByText("Speed test completed on Section S2")).toBeDefined();
  });

  it("switches to shift handover console and allows signing handover", () => {
    render(
      <CoordinationAndHandover
        territoryName="Northern Section"
        simTime="06:24"
        activeTrainsCount={4}
        delayedTrainsCount={1}
        openConflictsCount={2}
        activeRestrictionsCount={1}
      />
    );

    const handoverTab = screen.getByRole("button", { name: /Shift Handover Console/i });
    fireEvent.click(handoverTab);

    // Handover summary
    expect(screen.getByText("Northern Section")).toBeDefined();
    expect(screen.getByText(/4 Running/i)).toBeDefined();
    expect(screen.getByText(/2 Open/i)).toBeDefined();

    // Sign shift transfer
    const signBtn = screen.getByRole("button", { name: /Sign & Transfer Shift/i });
    fireEvent.click(signBtn);

    expect(screen.getByText(/✓ Handover Briefing Signed/i)).toBeDefined();
  });
});
