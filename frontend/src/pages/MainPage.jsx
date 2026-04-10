import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

function MiniTxItem({ tx }) {
  const isExpense = tx.type === "EXPENSE";
  return (
    <Link
      to={`/transactions/${tx.id}`}
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0.5rem 0",
        borderBottom: "1px solid var(--border)",
        textDecoration: "none",
        color: "inherit",
      }}
    >
      <div>
        <div style={{ fontSize: "0.9rem" }}>{tx.counterpart}</div>
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{tx.date}</div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        {tx.status === "PENDING" && (
          <span className="badge" style={{ background: "var(--yellow)", color: "#000" }}>
            Pendiente
          </span>
        )}
        <span style={{ fontWeight: 600, color: isExpense ? "var(--red)" : "var(--green)" }}>
          {isExpense ? "-" : "+"}${tx.amount.toLocaleString("es-CL")}
        </span>
      </div>
    </Link>
  );
}

function MiniFeed({ title, items, linkTo, emptyMsg }) {
  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
        <h3 style={{ fontSize: "1rem" }}>{title}</h3>
        <Link to={linkTo} style={{ fontSize: "0.85rem" }}>Ver todo →</Link>
      </div>
      {items.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>{emptyMsg}</p>
      ) : (
        items.slice(0, 5).map((tx) => <MiniTxItem key={tx.id} tx={tx} />)
      )}
    </div>
  );
}

export default function MainPage() {
  const [expenses, setExpenses] = useState([]);
  const [incomes, setIncomes] = useState([]);
  const [pending, setPending] = useState([]);

  useEffect(() => {
    api.getTransactions({ type: "EXPENSE" }).then((txs) => setExpenses(txs.slice(0, 5)));
    api.getTransactions({ type: "INCOME" }).then((txs) => setIncomes(txs.slice(0, 5)));
    api.getTransactions({ status: "PENDING" }).then(setPending);
  }, []);

  return (
    <div style={{ maxWidth: 700 }}>
      {pending.length > 0 && (
        <MiniFeed
          title={`Pendientes (${pending.length})`}
          items={pending}
          linkTo="/transactions?status=PENDING"
          emptyMsg=""
        />
      )}
      <MiniFeed
        title="Gastos recientes"
        items={expenses}
        linkTo="/transactions?type=EXPENSE"
        emptyMsg="Sin gastos registrados"
      />
      <MiniFeed
        title="Ingresos recientes"
        items={incomes}
        linkTo="/transactions?type=INCOME"
        emptyMsg="Sin ingresos registrados"
      />
    </div>
  );
}
