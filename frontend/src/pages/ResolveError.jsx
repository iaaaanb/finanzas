import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function ResolveError() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [email, setEmail] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [error, setError] = useState(null);

  const [form, setForm] = useState({
    type: "EXPENSE",
    amount: "",
    date: new Date().toISOString().split("T")[0],
    counterpart: "",
    account_id: "",
  });

  useEffect(() => {
    api.getEmail(id).then(setEmail);
    api.getAccounts().then((accs) => {
      setAccounts(accs);
      if (accs.length > 0) setForm((f) => ({ ...f, account_id: accs[0].id }));
    });
  }, [id]);

  if (!email) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const tx = await api.resolveEmail(id, {
        ...form,
        amount: Number(form.amount),
        account_id: Number(form.account_id),
      });
      navigate(`/transactions/${tx.id}`);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div style={{ maxWidth: 900 }}>
      <h1 style={{ marginBottom: "1rem" }}>Resolver error de parseo</h1>

      {/* Email preview */}
      <div className="card" style={{ marginBottom: "1rem" }}>
        <div style={{ marginBottom: "0.5rem" }}>
          <strong>{email.subject}</strong>
          <span style={{ color: "var(--text-muted)", marginLeft: 8, fontSize: "0.85rem" }}>
            {email.sender}
          </span>
        </div>
        <iframe
          srcDoc={email.body_html}
          sandbox=""
          style={{
            width: "100%",
            height: 400,
            border: "1px solid var(--border)",
            borderRadius: 6,
            background: "white",
          }}
          title="Email preview"
        />
      </div>

      {error && (
        <div style={{ background: "var(--red)", color: "white", padding: "0.5rem 0.75rem", borderRadius: 6, marginBottom: "1rem", fontSize: "0.85rem" }}>
          {error}
        </div>
      )}

      {/* Formulario */}
      <form onSubmit={handleSubmit} className="card">
        <div style={{ display: "flex", gap: "1rem" }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Tipo</label>
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
              <option value="EXPENSE">Gasto</option>
              <option value="INCOME">Ingreso</option>
            </select>
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Monto (CLP)</label>
            <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
          </div>
        </div>

        <div style={{ display: "flex", gap: "1rem" }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Fecha</label>
            <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Cuenta</label>
            <select value={form.account_id} onChange={(e) => setForm({ ...form, account_id: e.target.value })} required>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.name} ({a.bank})</option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Contraparte</label>
          <input value={form.counterpart} onChange={(e) => setForm({ ...form, counterpart: e.target.value })} required />
        </div>

        <button type="submit" className="btn-primary">Crear transacción</button>
      </form>
    </div>
  );
}
