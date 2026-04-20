import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useRefresh } from "./RefreshContext";

function formatRelative(dt) {
  if (!dt) return null;
  const diffSec = Math.floor((Date.now() - new Date(dt).getTime()) / 1000);
  if (diffSec < 60) return `hace ${diffSec}s`;
  if (diffSec < 3600) return `hace ${Math.floor(diffSec / 60)} min`;
  if (diffSec < 86400) return `hace ${Math.floor(diffSec / 3600)} h`;
  return `hace ${Math.floor(diffSec / 86400)} d`;
}

export default function Sidebar() {
  const [accounts, setAccounts] = useState([]);
  const [budgets, setBudgets] = useState([]);
  const [syncStatus, setSyncStatus] = useState(null);
  const { key } = useRefresh();

  useEffect(() => {
    api.getAccounts().then(setAccounts);
    api.getBudgets().then(setBudgets);
    api.getSyncStatus().then(setSyncStatus).catch(() => {});
  }, [key]);

  const total = accounts.reduce((s, a) => s + a.balance, 0);

  const lastRun = syncStatus?.last_run;
  const activeRun = syncStatus?.active_run;
  // Color del indicador: amarillo si hay un run activo, rojo si el último falló,
  // gris si no hay nada o todo está bien.
  const dotColor = activeRun
    ? "var(--yellow)"
    : lastRun?.status === "FAILED"
    ? "var(--red)"
    : "var(--text-muted)";

  return (
    <aside
      style={{
        width: 280,
        background: "var(--bg-card)",
        borderRight: "1px solid var(--border)",
        padding: "1.5rem 1rem",
        display: "flex",
        flexDirection: "column",
        gap: "1.5rem",
        overflowY: "auto",
      }}
    >
      <div>
        <Link to="/" style={{ fontSize: "1.25rem", fontWeight: 700 }}>
          Finanzas
        </Link>
      </div>

      <div>
        <h3 style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
          SALDOS
        </h3>
        <div style={{ fontWeight: 700, fontSize: "1.1rem", marginBottom: "0.5rem" }}>
          ${total.toLocaleString("es-CL")}
        </div>
        {accounts.map((a) => (
          <div
            key={a.id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "0.3rem 0",
              fontSize: "0.9rem",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: a.color,
                }}
              />
              {a.name}
            </span>
            <span>${a.balance.toLocaleString("es-CL")}</span>
          </div>
        ))}
      </div>

      <div>
        <h3 style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
          PRESUPUESTOS
        </h3>
        {budgets.map((b) => {
          const period = b.active_period;
          if (!period) return null;
          const spent = period.starting_amount - period.balance;
          const pct = Math.min((spent / period.starting_amount) * 100, 100);
          const over = period.balance < 0;
          return (
            <Link
              to={`/budgets/${b.id}`}
              key={b.id}
              style={{
                display: "block",
                marginBottom: "0.75rem",
                textDecoration: "none",
                color: "inherit",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.85rem",
                  marginBottom: 4,
                }}
              >
                <span>{b.name}</span>
                <span style={{ color: over ? "var(--red)" : "var(--text-muted)" }}>
                  ${period.balance.toLocaleString("es-CL")} / $
                  {period.starting_amount.toLocaleString("es-CL")}
                </span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{
                    width: `${pct}%`,
                    background: over ? "var(--red)" : b.color,
                  }}
                />
              </div>
            </Link>
          );
        })}
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        <h3 style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>
          GESTIÓN
        </h3>
        <Link to="/transactions/new">+ Nueva transacción</Link>
        <Link to="/accounts">Cuentas</Link>
        <Link to="/categories">Categorías</Link>
        <Link to="/budgets">Presupuestos</Link>
        <Link
          to="/sync"
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
        >
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: dotColor,
              }}
            />
            Sincronización
          </span>
          {lastRun && !activeRun && (
            <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
              {formatRelative(lastRun.finished_at || lastRun.started_at)}
            </span>
          )}
          {activeRun && (
            <span style={{ fontSize: "0.7rem", color: "var(--yellow)" }}>
              corriendo…
            </span>
          )}
        </Link>
      </nav>
    </aside>
  );
}
