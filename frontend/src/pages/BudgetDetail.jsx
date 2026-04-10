import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";

const TYPE_LABELS = { L_V: "Lun–Vie", V_D: "Vie–Dom", L_D: "Lun–Dom", MONTHLY: "Mensual" };

export default function BudgetDetail() {
  const { id } = useParams();
  const [budget, setBudget] = useState(null);
  const [periods, setPeriods] = useState([]);
  const [expandedPeriod, setExpandedPeriod] = useState(null);
  const [periodTxs, setPeriodTxs] = useState({});

  useEffect(() => {
    api.getBudget(id).then(setBudget);
    api.getBudgetPeriods(id).then(setPeriods);
  }, [id]);

  const togglePeriod = async (periodId) => {
    if (expandedPeriod === periodId) {
      setExpandedPeriod(null);
      return;
    }
    setExpandedPeriod(periodId);
    if (!periodTxs[periodId]) {
      const txs = await api.getTransactions({ budget_period_id: periodId });
      setPeriodTxs((prev) => ({ ...prev, [periodId]: txs }));
    }
  };

  if (!budget) return null;

  const active = periods.find((p) => !p.closed_at);
  const closed = periods.filter((p) => p.closed_at);

  return (
    <div style={{ maxWidth: 600 }}>
      <h1 style={{ marginBottom: "0.25rem" }}>{budget.name}</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
        {TYPE_LABELS[budget.type]} · ${budget.amount.toLocaleString("es-CL")} por período
      </p>

      {active && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ marginBottom: "0.5rem" }}>Período activo</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
            {active.period_start} → {active.period_end}
          </p>
          <p style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0.5rem 0" }}>
            ${active.balance.toLocaleString("es-CL")}
            <span style={{ fontSize: "0.85rem", fontWeight: 400, color: "var(--text-muted)" }}>
              {" "}/ ${active.starting_amount.toLocaleString("es-CL")}
            </span>
          </p>
        </div>
      )}

      {closed.length > 0 && (
        <div>
          <h3 style={{ marginBottom: "0.75rem" }}>Historial</h3>
          {closed.map((p) => (
            <div key={p.id} className="card" style={{ marginBottom: "0.5rem" }}>
              <div
                style={{ display: "flex", justifyContent: "space-between", cursor: "pointer" }}
                onClick={() => togglePeriod(p.id)}
              >
                <span style={{ fontSize: "0.9rem" }}>
                  {p.period_start} → {p.period_end}
                </span>
                <span style={{ color: p.final_balance < 0 ? "var(--red)" : "var(--green)", fontWeight: 600 }}>
                  ${p.final_balance?.toLocaleString("es-CL")}
                </span>
              </div>
              {expandedPeriod === p.id && periodTxs[p.id] && (
                <div style={{ marginTop: "0.75rem", paddingTop: "0.75rem", borderTop: "1px solid var(--border)" }}>
                  {periodTxs[p.id].length === 0 ? (
                    <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Sin transacciones</p>
                  ) : (
                    periodTxs[p.id].map((tx) => (
                      <Link
                        to={`/transactions/${tx.id}`}
                        key={tx.id}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          padding: "0.3rem 0",
                          fontSize: "0.85rem",
                          color: "inherit",
                          textDecoration: "none",
                        }}
                      >
                        <span>{tx.counterpart}</span>
                        <span style={{ color: "var(--red)" }}>-${tx.amount.toLocaleString("es-CL")}</span>
                      </Link>
                    ))
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
