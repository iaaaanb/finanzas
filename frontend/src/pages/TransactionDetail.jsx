import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useRefresh } from "../components/RefreshContext";

export default function TransactionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { triggerRefresh } = useRefresh();
  const [tx, setTx] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [budgets, setBudgets] = useState([]);
  const [counterparts, setCounterparts] = useState([]);
  const [form, setForm] = useState({});
  const [rememberCat, setRememberCat] = useState(false);
  const [rememberBudget, setRememberBudget] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getAccounts().then(setAccounts);
    api.getCategories().then(setCategories);
    api.getBudgets().then(setBudgets);
    api.getCounterparts().then(setCounterparts);
  }, []);

  useEffect(() => {
    api.getTransaction(id).then((t) => {
      setTx(t);
      setForm({
        amount: t.amount,
        date: t.date,
        counterpart: t.counterpart,
        comment: t.comment || "",
        account_id: t.account_id,
        category_id: t.category_id || "",
        budget_period_id: t.budget_period_id || "",
      });
      api.getAutoAssignByCounterpart(t.counterpart).then((rule) => {
        if (rule.category_id) setRememberCat(true);
        if (rule.budget_id) setRememberBudget(true);
      }).catch(() => {});
    });
  }, [id]);

  if (!tx) return null;

  const isExpense = tx.type === "EXPENSE";
  const isPending = tx.status === "PENDING";

  const getActivePeriodId = (budgetId) => {
    const b = budgets.find((b) => b.id === Number(budgetId));
    return b?.active_period?.id || "";
  };

  const handleSave = async () => {
    setError(null);
    try {
      const payload = {
        amount: Number(form.amount),
        date: form.date,
        counterpart: form.counterpart,
        comment: form.comment || null,
        account_id: Number(form.account_id),
        category_id: form.category_id ? Number(form.category_id) : null,
        budget_period_id: form.budget_period_id ? Number(form.budget_period_id) : null,
        remember_category: rememberCat,
        remember_budget: rememberBudget,
      };
      const updated = await api.updateTransaction(id, payload);
      setTx(updated);
      triggerRefresh();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleConfirm = async () => {
    setError(null);
    try {
      await handleSave();
      const confirmed = await api.confirmTransaction(id);
      setTx(confirmed);
      triggerRefresh();
    } catch (e) {
      setError(e.message);
    }
  };

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
        updates.budget_period_id = getActivePeriodId(rule.budget_id);
        setRememberBudget(true);
      }
      if (Object.keys(updates).length > 0) {
        setForm((f) => ({ ...f, ...updates }));
      }
    } catch {}
  };

  const selectedBudgetId = (() => {
    if (!form.budget_period_id) return "";
    const b = budgets.find(
      (b) => b.active_period?.id === Number(form.budget_period_id)
    );
    return b ? b.id : "";
  })();

  const handleBudgetChange = (budgetId) => {
    if (!budgetId) {
      setForm({ ...form, budget_period_id: "" });
    } else {
      setForm({ ...form, budget_period_id: getActivePeriodId(budgetId) });
    }
  };

  return (
    <div style={{ maxWidth: 500 }}>
      <h1 style={{ marginBottom: "0.25rem" }}>
        {isExpense ? "Gasto" : "Ingreso"}
        {isPending && (
          <span className="badge" style={{ background: "var(--yellow)", color: "#000", marginLeft: 10, fontSize: "0.7rem", verticalAlign: "middle" }}>
            Pendiente
          </span>
        )}
      </h1>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
        Creada el {tx.created_at.split("T")[0]}
        {tx.email_id && <span> · Desde email #{tx.email_id}</span>}
      </p>

      {error && (
        <div style={{ background: "var(--red)", color: "white", padding: "0.5rem 0.75rem", borderRadius: 6, marginBottom: "1rem", fontSize: "0.85rem" }}>
          {error}
        </div>
      )}

      <div className="card">
        <div className="form-group">
          <label>Monto (CLP)</label>
          <input
            type="number"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
          />
        </div>

        <div style={{ display: "flex", gap: "1rem" }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Fecha</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
            />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Cuenta</label>
            <select
              value={form.account_id}
              onChange={(e) => setForm({ ...form, account_id: e.target.value })}
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Contraparte</label>
          <input
            value={form.counterpart}
            onChange={(e) => setForm({ ...form, counterpart: e.target.value })}
            onBlur={handleCounterpartBlur}
            list="counterparts-list"
          />
          <datalist id="counterparts-list">
            {counterparts.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </div>

        {isExpense && (
          <div className="form-group">
            <label>Presupuesto (obligatorio)</label>
            <select
              value={selectedBudgetId}
              onChange={(e) => handleBudgetChange(e.target.value)}
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

        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
          {isPending ? (
            <button className="btn-primary" onClick={handleConfirm}>
              Confirmar
            </button>
          ) : (
            <button className="btn-primary" onClick={handleSave}>
              Guardar
            </button>
          )}
          <button className="btn-secondary" onClick={() => navigate(-1)}>
            Volver
          </button>
        </div>
      </div>
    </div>
  );
}
