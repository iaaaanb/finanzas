import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";

export default function TransactionFeed() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [transactions, setTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [budgets, setBudgets] = useState([]);

  const filters = {
    type: searchParams.get("type"),
    status: searchParams.get("status"),
    account_id: searchParams.get("account_id"),
    category_id: searchParams.get("category_id"),
  };

  const setFilter = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  };

  useEffect(() => {
    api.getAccounts().then(setAccounts);
    api.getCategories().then(setCategories);
    api.getBudgets().then(setBudgets);
  }, []);

  useEffect(() => {
    const params = {};
    for (const [k, v] of searchParams.entries()) params[k] = v;
    api.getTransactions(params).then(setTransactions);
  }, [searchParams]);

  return (
    <div style={{ maxWidth: 700 }}>
      <h1 style={{ marginBottom: "1rem" }}>Transacciones</h1>

      {/* Filtros */}
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <select
          value={filters.type || ""}
          onChange={(e) => setFilter("type", e.target.value)}
          style={{ width: "auto" }}
        >
          <option value="">Todos los tipos</option>
          <option value="EXPENSE">Gastos</option>
          <option value="INCOME">Ingresos</option>
        </select>

        <select
          value={filters.status || ""}
          onChange={(e) => setFilter("status", e.target.value)}
          style={{ width: "auto" }}
        >
          <option value="">Todos los estados</option>
          <option value="PENDING">Pendientes</option>
          <option value="CONFIRMED">Confirmados</option>
        </select>

        <select
          value={filters.account_id || ""}
          onChange={(e) => setFilter("account_id", e.target.value)}
          style={{ width: "auto" }}
        >
          <option value="">Todas las cuentas</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>

        <select
          value={filters.category_id || ""}
          onChange={(e) => setFilter("category_id", e.target.value)}
          style={{ width: "auto" }}
        >
          <option value="">Todas las categorías</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* Lista */}
      {transactions.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>No hay transacciones con estos filtros.</p>
      ) : (
        transactions.map((tx) => {
          const isExpense = tx.type === "EXPENSE";
          return (
            <Link
              to={`/transactions/${tx.id}`}
              key={tx.id}
              className="card"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "0.5rem",
                textDecoration: "none",
                color: "inherit",
              }}
            >
              <div>
                <div style={{ fontWeight: 500 }}>{tx.counterpart}</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  {tx.date}
                  {tx.status === "PENDING" && (
                    <span className="badge" style={{ background: "var(--yellow)", color: "#000", marginLeft: 8 }}>
                      Pendiente
                    </span>
                  )}
                </div>
              </div>
              <span style={{ fontWeight: 600, color: isExpense ? "var(--red)" : "var(--green)" }}>
                {isExpense ? "-" : "+"}${tx.amount.toLocaleString("es-CL")}
              </span>
            </Link>
          );
        })
      )}
    </div>
  );
}
