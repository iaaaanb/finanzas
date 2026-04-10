import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const TYPE_LABELS = { L_V: "Lun–Vie", V_D: "Vie–Dom", L_D: "Lun–Dom", MONTHLY: "Mensual" };

export default function Budgets() {
  const [budgets, setBudgets] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", type: "L_D", color: "#3b82f6", amount: "" });

  const load = () => api.getBudgets().then(setBudgets);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    await api.createBudget({ ...form, amount: Number(form.amount) });
    setForm({ name: "", type: "L_D", color: "#3b82f6", amount: "" });
    setShowForm(false);
    load();
  };

  return (
    <div style={{ maxWidth: 600 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h1>Presupuestos</h1>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancelar" : "+ Nuevo"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="card" style={{ marginBottom: "1rem" }}>
          <div className="form-group">
            <label>Nombre</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div style={{ display: "flex", gap: "1rem" }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Tipo</label>
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                <option value="L_V">Lun–Vie</option>
                <option value="V_D">Vie–Dom</option>
                <option value="L_D">Lun–Dom</option>
                <option value="MONTHLY">Mensual</option>
              </select>
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Monto</label>
              <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
            </div>
            <div className="form-group" style={{ width: 60 }}>
              <label>Color</label>
              <input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
            </div>
          </div>
          <button type="submit" className="btn-primary">Crear</button>
        </form>
      )}

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
            className="card"
            style={{ display: "block", marginBottom: "0.5rem", textDecoration: "none", color: "inherit" }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 12, height: 12, borderRadius: "50%", background: b.color }} />
                <strong>{b.name}</strong>
                <span className="badge" style={{ background: "var(--bg-input)" }}>{TYPE_LABELS[b.type]}</span>
              </span>
              <span style={{ color: over ? "var(--red)" : "var(--text-muted)" }}>
                ${period.balance.toLocaleString("es-CL")} / ${period.starting_amount.toLocaleString("es-CL")}
              </span>
            </div>
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${pct}%`, background: over ? "var(--red)" : b.color }} />
            </div>
          </Link>
        );
      })}
    </div>
  );
}
