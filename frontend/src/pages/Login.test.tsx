import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "./Login";

const login = vi.fn();

vi.mock("../auth", () => ({
  useAuth: () => ({
    login,
    user: null,
    initialising: false,
    logout: vi.fn(),
  }),
}));

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<div>Dashboard destination</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  login.mockReset();
});

describe("LoginPage", () => {
  it("shows both demo roles and the synthetic-data disclaimer", () => {
    renderLogin();
    expect(screen.getByText("Section Master")).toBeInTheDocument();
    expect(screen.getByText("Station Master")).toBeInTheDocument();
    expect(screen.getByText(/all data is synthetic/i)).toBeInTheDocument();
  });

  it("fills demo credentials when a demo account is clicked", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByText("Station Master"));
    expect(screen.getByLabelText("Username")).toHaveValue("station.master");
    expect(screen.getByLabelText("Password")).toHaveValue("Station@123");
  });

  it("signs in and navigates to the dashboard", async () => {
    const user = userEvent.setup();
    login.mockResolvedValue(undefined);
    renderLogin();
    await user.click(screen.getByText("Section Master"));
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() =>
      expect(login).toHaveBeenCalledWith("section.master", "Section@123"),
    );
    expect(await screen.findByText("Dashboard destination")).toBeInTheDocument();
  });

  it("shows the server error and does not navigate", async () => {
    const user = userEvent.setup();
    login.mockRejectedValue(new Error("Invalid username or password"));
    renderLogin();
    await user.click(screen.getByText("Section Master"));
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid username or password",
    );
    expect(screen.queryByText("Dashboard destination")).not.toBeInTheDocument();
  });
});
