import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function AccountDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState(null);

  useEffect(() => {
    api.getAccount(id).then((a) =>
      setForm({
        name: a.name,
        bank: a.bank,
        color: a.color,
        balance: a.balance,
        account_number: a.account_number || "",
      })
    );
  }, [id]);

  if (!form) return null;

  const handleSave = async (e) => {
    e.preventDefault();
    await api.updateAccount(id, {
      ...form,
      balance: Number(form.balance),
      account_number: form.account_number.trim() || null,
    });
    navigate("/accounts");
  };

  return (
    <div style={{ maxWidth: 500 }}>
      <h1 style={{ marginBottom: "1rem" }}>Editar cuenta</h1>
      <form onSubmit={handleSave} className="card">
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
            <label>Saldo</label>
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
        <button type="submit" className="btn-primary">Guardar</button>
      </form>
    </div>
  );
}
