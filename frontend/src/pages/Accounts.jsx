import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Accounts() {
  const [accounts, setAccounts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    bank: "",
    color: "#3b82f6",
    balance: 0,
    account_number: "",
  });
  const navigate = useNavigate();

  useEffect(() => {
    api.getAccounts().then(setAccounts);
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    await api.createAccount({
      ...form,
      balance: Number(form.balance),
      account_number: form.account_number.trim() || null,
    });
    setForm({ name: "", bank: "", color: "#3b82f6", balance: 0, account_number: "" });
    setShowForm(false);
    api.getAccounts().then(setAccounts);
  };

  return (
    <div style={{ maxWidth: 600 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h1>Cuentas</h1>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancelar" : "+ Nueva"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="card" style={{ marginBottom: "1rem" }}>
          <div className="form-group">
            <label>Nombre</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Banco</label>
            <input value={form.bank} onChange={(e) => setForm({ ...form, bank: e.target.value })} required />
          </div>
          <div style={{ display: "flex", gap: "1rem" }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Color</label>
              <input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Saldo inicial</label>
              <input type="number" value={form.balance} onChange={(e) => setForm({ ...form, balance: e.target.value })} />
            </div>
          </div>
          <div className="form-group">
            <label>Últimos 4 dígitos de la cuenta</label>
            <input
              value={form.account_number}
              onChange={(e) => setForm({ ...form, account_number: e.target.value })}
              maxLength={4}
              placeholder="ej: 5092"
            />
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Usado para asignar emails entrantes a esta cuenta
            </span>
          </div>
          <button type="submit" className="btn-primary">Crear</button>
        </form>
      )}

      {accounts.map((a) => (
        <Link
          to={`/accounts/${a.id}`}
          key={a.id}
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
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: a.color }} />
            <span>
              <strong>{a.name}</strong>
              <span style={{ color: "var(--text-muted)", marginLeft: 8, fontSize: "0.85rem" }}>
                {a.bank}
                {a.account_number && (
                  <span style={{ marginLeft: 6 }}>· ****{a.account_number}</span>
                )}
              </span>
            </span>
          </span>
          <span style={{ fontWeight: 600 }}>${a.balance.toLocaleString("es-CL")}</span>
        </Link>
      ))}
    </div>
  );
}
