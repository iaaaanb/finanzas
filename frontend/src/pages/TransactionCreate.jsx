import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useRefresh } from "../components/RefreshContext";

export default function TransactionCreate() {
  const navigate = useNavigate();
  const { triggerRefresh } = useRefresh();
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [budgets, setBudgets] = useState([]);
  const [counterparts, setCounterparts] = useState([]);
  const [error, setError] = useState(null);

  const [form, setForm] = useState({
    type: "EXPENSE",
    amount: "",
    date: new Date().toISOString().split("T")[0],
    counterpart: "",
    comment: "",
    account_id: "",
    category_id: "",
    budget_id: "",
  });
  const [rememberCat, setRememberCat] = useState(false);
  const [rememberBudget, setRememberBudget] = useState(false);

  useEffect(() => {
    api.getAccounts().then((accs) => {
      setAccounts(accs);
      if (accs.length > 0 && !form.account_id) {
        setForm((f) => ({ ...f, account_id: accs[0].id }));
      }
    });
    api.getCategories().then(setCategories);
    api.getBudgets().then(setBudgets);
    api.getCounterparts().then(setCounterparts);
  }, []);

  const handleCounterpartBlur = async () => {
    if (!form.counterpart.trim()) return;
    try {
      const rule = await api.getAutoAssignByCounterpart(form.counterpart.trim());
      const updates = {};
      if (rule.category_id) {
        updates.category_id = rule.category_id;
        setRememberCat(true);
      }
      if (rule.budget_id) {
        updates.budget_id = rule.budget_id;
        setRememberBudget(true);
      }
      if (Object.keys(updates).length > 0) {
        setForm((f) => ({ ...f, ...updates }));
      }
    } catch {}
  };

  const isExpense = form.type === "EXPENSE";

  const getActivePeriodId = (budgetId) => {
    const b = budgets.find((b) => b.id === Number(budgetId));
    return b?.active_period?.id || null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const periodId = isExpense && form.budget_id
      ? getActivePeriodId(form.budget_id)
      : null;

    try {
      const tx = await api.createTransaction({
        type: form.type,
        amount: Number(form.amount),
        date: form.date,
        counterpart: form.counterpart,
        comment: form.comment || null,
        account_id: Number(form.account_id),
        category_id: form.category_id ? Number(form.category_id) : null,
        budget_period_id: periodId,
        remember_category: rememberCat,
        remember_budget: rememberBudget,
      });
      triggerRefresh();
      navigate(`/transactions/${tx.id}`);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div style={{ maxWidth: 500 }}>
      <h1 style={{ marginBottom: "1rem" }}>Nueva transacción</h1>

      {error && (
        <div style={{ background: "var(--red)", color: "white", padding: "0.5rem 0.75rem", borderRadius: 6, marginBottom: "1rem", fontSize: "0.85rem" }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card">
        <div className="form-group">
          <label>Tipo</label>
          <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            <option value="EXPENSE">Gasto</option>
            <option value="INCOME">Ingreso</option>
          </select>
        </div>

        <div style={{ display: "flex", gap: "1rem" }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Monto (CLP)</label>
            <input
              type="number"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              required
            />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Fecha</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label>Cuenta</label>
          <select
            value={form.account_id}
            onChange={(e) => setForm({ ...form, account_id: e.target.value })}
            required
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Contraparte</label>
          <input
            value={form.counterpart}
            onChange={(e) => setForm({ ...form, counterpart: e.target.value })}
            onBlur={handleCounterpartBlur}
            list="counterparts-list-create"
            required
          />
          <datalist id="counterparts-list-create">
            {counterparts.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </div>

        {isExpense && (
          <div className="form-group">
            <label>Presupuesto (obligatorio)</label>
            <select
              value={form.budget_id}
              onChange={(e) => setForm({ ...form, budget_id: e.target.value })}
            >
              <option value="">— Seleccionar —</option>
              {budgets.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
            <label style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6, fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <input
                type="checkbox"
                checked={rememberBudget}
                onChange={(e) => setRememberBudget(e.target.checked)}
                style={{ width: "auto" }}
              />
              Recordar para "{form.counterpart}"
            </label>
          </div>
        )}

        <div className="form-group">
          <label>Categoría (opcional)</label>
          <select
            value={form.category_id}
            onChange={(e) => setForm({ ...form, category_id: e.target.value })}
          >
            <option value="">— Sin categoría —</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6, fontSize: "0.85rem", color: "var(--text-muted)" }}>
            <input
              type="checkbox"
              checked={rememberCat}
              onChange={(e) => setRememberCat(e.target.checked)}
              style={{ width: "auto" }}
            />
            Recordar para "{form.counterpart}"
          </label>
        </div>

        <div className="form-group">
          <label>Comentario</label>
          <textarea
            value={form.comment}
            onChange={(e) => setForm({ ...form, comment: e.target.value })}
            rows={2}
          />
        </div>

        <button type="submit" className="btn-primary">
          Crear transacción
        </button>
      </form>
    </div>
  );
}
