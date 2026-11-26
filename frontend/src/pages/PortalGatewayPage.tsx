import { Link } from "react-router-dom";

export function PortalGatewayPage() {
  return (
    <div
      className="gateway-layout"
      style={{
        minHeight: "100vh",
        background: "radial-gradient(ellipse at center, #0f172a 0%, #020617 100%)",
        color: "#f8fafc",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "48px 24px",
      }}
    >
      <div style={{ maxWidth: "980px", width: "100%", textAlign: "center", marginBottom: "40px" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
          <span style={{ fontSize: "36px" }}>🚂</span>
          <span
            style={{
              fontSize: "14px",
              fontWeight: 800,
              letterSpacing: "2px",
              color: "#38bdf8",
              textTransform: "uppercase",
            }}
          >
            Indian Railways Operational Decision Support
          </span>
        </div>
        <h1
          style={{
            fontSize: "clamp(2.2rem, 4vw, 3.2rem)",
            fontWeight: 800,
            margin: "0 0 12px 0",
            background: "linear-gradient(135deg, #f8fafc 0%, #cbd5e1 50%, #94a3b8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          RAILGORITHM Operations Access Gateways
        </h1>
        <p style={{ fontSize: "1.1rem", color: "#94a3b8", maxWidth: "680px", margin: "0 auto", lineHeight: 1.5 }}>
          Select your operational role gateway. Authentication and workspaces are strictly role-isolated
          in compliance with Indian Railways operating procedures.
        </p>
      </div>

      <div
        style={{
          maxWidth: "980px",
          width: "100%",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "28px",
        }}
      >
        {/* Gateway Card 1: Station Master Portal */}
        <div
          style={{
            background: "linear-gradient(180deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%)",
            border: "2px solid #f59e0b",
            borderRadius: "14px",
            padding: "36px 28px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            boxShadow: "0 20px 25px -5px rgba(245, 158, 11, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.5)",
            transition: "transform 0.2s ease, box-shadow 0.2s ease",
          }}
        >
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
              <span style={{ fontSize: "40px" }}>🚉</span>
              <span
                style={{
                  background: "#f59e0b",
                  color: "#0f172a",
                  fontWeight: 800,
                  fontSize: "11px",
                  padding: "4px 10px",
                  borderRadius: "4px",
                  letterSpacing: "1px",
                  textTransform: "uppercase",
                }}
              >
                Local Yard Authority
              </span>
            </div>

            <h2 style={{ fontSize: "1.65rem", fontWeight: 700, margin: "0 0 10px 0", color: "#f8fafc" }}>
              Station Master Portal
            </h2>

            <p style={{ color: "#94a3b8", fontSize: "0.95rem", lineHeight: 1.5, margin: "0 0 20px 0" }}>
              For Station Masters and yard operators. Manages station-specific track layouts, platform berthing,
              local shunting, train arrival/departure movements, and adjacent block token clearance.
            </p>

            <ul style={{ listStyle: "none", padding: 0, margin: "0 0 24px 0", display: "flex", flexDirection: "column", gap: "8px" }}>
              <li style={{ fontSize: "0.88rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#f59e0b" }}>▸</span> Dedicated station yard working diagram
              </li>
              <li style={{ fontSize: "0.88rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#f59e0b" }}>▸</span> Platform & line occupancy monitor
              </li>
              <li style={{ fontSize: "0.88rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#f59e0b" }}>▸</span> Adjacent station block awareness & line clear
              </li>
              <li style={{ fontSize: "0.88rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#f59e0b" }}>▸</span> Station-local alert resolution
              </li>
            </ul>
          </div>

          <Link
            to="/login/station-master"
            style={{
              display: "block",
              textAlign: "center",
              background: "#f59e0b",
              color: "#0f172a",
              fontWeight: 800,
              fontSize: "1.05rem",
              padding: "14px",
              borderRadius: "8px",
              textDecoration: "none",
              boxShadow: "0 4px 6px -1px rgba(245, 158, 11, 0.4)",
            }}
          >
            Enter Station Master Portal →
          </Link>
        </div>

        {/* Gateway Card 2: Section Controller Portal */}
        <div
          style={{
            background: "linear-gradient(180deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%)",
            border: "2px solid #0284c7",
            borderRadius: "14px",
            padding: "36px 28px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            boxShadow: "0 20px 25px -5px rgba(2, 132, 199, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.5)",
            transition: "transform 0.2s ease, box-shadow 0.2s ease",
          }}
        >
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
              <span style={{ fontSize: "40px" }}>🎛️</span>
              <span
                style={{
                  background: "#0284c7",
                  color: "#f8fafc",
                  fontWeight: 800,
                  fontSize: "11px",
                  padding: "4px 10px",
                  borderRadius: "4px",
                  letterSpacing: "1px",
                  textTransform: "uppercase",
                }}
              >
                Territory Dispatch Desk
              </span>
            </div>

            <h2 style={{ fontSize: "1.65rem", fontWeight: 700, margin: "0 0 10px 0", color: "#f8fafc" }}>
              Section Controller Portal
            </h2>

            <p style={{ color: "#94a3b8", fontSize: "0.95rem", lineHeight: 1.5, margin: "0 0 20px 0" }}>
              For Divisional Section Controllers and Chief Dispatchers. Supervises whole-corridor traffic,
              Master Control Graph time-distance lines, single-line bottlenecks, and junction crossing decisions.
            </p>

            <ul style={{ listStyle: "none", padding: 0, margin: "0 0 24px 0", display: "flex", flexDirection: "column", gap: "8px" }}>
              <li style={{ fontSize: "0.88rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#38bdf8" }}>▸</span> Whole-corridor topology strip & bottleneck tracker
              </li>
              <li style={{ fontSize: "0.88rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#38bdf8" }}>▸</span> Master Control Graph (Interactive Trajectories)
              </li>
              <li style={{ fontSize: "0.88rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#38bdf8" }}>▸</span> Junction crossing & precedence regulation workspace
              </li>
              <li style={{ fontSize: "0.88rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#38bdf8" }}>▸</span> Corridor block section board & train ledger
              </li>
            </ul>
          </div>

          <Link
            to="/login/section-controller"
            style={{
              display: "block",
              textAlign: "center",
              background: "#0284c7",
              color: "#f8fafc",
              fontWeight: 800,
              fontSize: "1.05rem",
              padding: "14px",
              borderRadius: "8px",
              textDecoration: "none",
              boxShadow: "0 4px 6px -1px rgba(2, 132, 199, 0.4)",
            }}
          >
            Enter Section Controller Portal →
          </Link>
        </div>
      </div>

      <div style={{ marginTop: "40px", fontSize: "0.8rem", color: "#64748b", textAlign: "center" }}>
        SYNTHETIC DATA — Not real Indian Railways operational data. Recommendations are decision support only; a human operator must decide. No live railway interlocking connected.
      </div>
    </div>
  );
}
