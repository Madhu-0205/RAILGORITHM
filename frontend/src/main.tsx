import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { AuthProvider } from "./auth";
import { SimulationProvider } from "./simulation";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <SimulationProvider>
          <App />
        </SimulationProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
