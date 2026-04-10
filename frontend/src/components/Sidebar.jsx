import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useRefresh } from "./RefreshContext";

export default function Sidebar() {
  const [accounts, setAccounts] = useState([]);
  const [budgets, setBudgets] = useState([]);
  const { key } = useRefresh();

  useEffect(() => {
    api.getAccounts().then(setAccounts);
    api.getBudgets().then(setBudgets);
  }, [key]);

  const total = accounts.reduce((s, a) => s + a.balance, 0);

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
      </nav>
    </aside>
  );
}
