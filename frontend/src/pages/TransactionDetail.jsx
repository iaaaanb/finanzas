import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useRefresh } from "../components/RefreshContext";

export default function TransactionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { triggerRefresh } = useRefresh();
  const [tx, setTx] = useState(null);
  const [email, setEmail] = useState(null);
  const [showEmailBody, setShowEmailBody] = useState(false);
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [budgets, setBudgets] = useState([]);
  const [counterparts, setCounterparts] = useState([]);
  const [form, setForm] = useState({});
  const [rememberCat, setRememberCat] = useState(false);
  const [rememberBudget, setRememberBudget] = useState(false);
  const [autoConfirm, setAutoConfirm] = useState(false);
  const [error, setError] = useState(null);
  const [banner, setBanner] = useState(null); // para mensajes de éxito del sweep

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
        if (rule.auto_confirm) setAutoConfirm(true);
      }).catch(() => {});

      if (t.email_id) {
        api.getEmail(t.email_id).then(setEmail).catch(() => {});
      }
    });
  }, [id]);

  if (!tx) return null;

  const isExpense = tx.type === "EXPENSE";
  const isPending = tx.status === "PENDING";

  const getActivePeriodId = (budgetId) => {
    const b = budgets.find((b) => b.id === Number(budgetId));
    return b?.active_period?.id || "";
  };

  const savePayload = () => ({
    amount: Number(form.amount),
    date: form.date,
    counterpart: form.counterpart,
    comment: form.comment || null,
    account_id: Number(form.account_id),
    category_id: form.category_id ? Number(form.category_id) : null,
    budget_period_id: form.budget_period_id ? Number(form.budget_period_id) : null,
    remember_category: rememberCat,
    remember_budget: rememberBudget,
  });

  const handleSave = async () => {
    setError(null);
    try {
      const updated = await api.updateTransaction(id, savePayload());
      setTx(updated);
      triggerRefresh();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleConfirm = async () => {
    setError(null);
    try {
      // Guardar cambios del form antes de confirmar (mismo comportamiento que antes)
      await api.updateTransaction(id, savePayload());
      await api.confirmTransaction(id);
      triggerRefresh();
      // Al confirmar, volver a donde veníamos (típicamente el feed de pending).
      navigate(-1);
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
      if (rule.auto_confirm) setAutoConfirm(true);
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

  // Auto-confirm solo tiene sentido si hay categoría y presupuesto (para gastos).
  // Para ingresos no exigimos budget.
  const canEnableAutoConfirm =
    !!form.category_id && (!isExpense || !!form.budget_period_id);

  const handleEnableAutoConfirm = async () => {
    if (!canEnableAutoConfirm) return;
    setError(null);
    setBanner(null);
    try {
      // Primero guardamos el estado actual para que la regla se cree con los
      // category/budget correctos (vía los checkboxes Recordar, que forzamos).
      setRememberCat(true);
      setRememberBudget(true);
      await api.updateTransaction(id, {
        ...savePayload(),
        remember_category: true,
        remember_budget: true,
      });
      // Luego activamos auto_confirm + sweep de PENDING
      const resp = await api.enableAutoConfirm(form.counterpart.trim());
      setAutoConfirm(true);
      triggerRefresh();
      const msg =
        resp.retroactive_confirmed === 0
          ? "Auto-confirmación activada."
          : `Auto-confirmación activada. ${resp.retroactive_confirmed} transacción(es) pendiente(s) confirmadas.` +
            (resp.retroactive_skipped > 0
              ? ` ${resp.retroactive_skipped} saltadas (sin presupuesto).`
              : "");
      setBanner(msg);
      // La tx actual puede haberse confirmado en el sweep → refresh.
      const refreshed = await api.getTransaction(id);
      setTx(refreshed);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDisableAutoConfirm = async () => {
    setError(null);
    setBanner(null);
    try {
      await api.disableAutoConfirm(form.counterpart.trim());
      setAutoConfirm(false);
      setBanner("Auto-confirmación desactivada.");
    } catch (e) {
      setError(e.message);
    }
  };

  const gmailUrl = email
    ? `https://mail.google.com/mail/u/0/#all/${email.gmail_message_id}`
    : null;

  return (
    <div style={{ maxWidth: 500 }}>
      <h1 style={{ marginBottom: "0.25rem" }}>
        {isExpense ? "Gasto" : "Ingreso"}
        {isPending && (
          <span className="badge" style={{ background: "var(--yellow)", color: "#000", marginLeft: 10, fontSize: "0.7rem", verticalAlign: "middle" }}>
            Pendiente
          </span>
        )}
        {autoConfirm && (
          <span className="badge" style={{ background: "var(--green)", color: "white", marginLeft: 6, fontSize: "0.7rem", verticalAlign: "middle" }}>
            Auto
          </span>
        )}
      </h1>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
        Creada el {tx.created_at.split("T")[0]}
        {tx.email_id && <span> · Desde email #{tx.email_id}</span>}
      </p>

      {email && (
        <div className="card" style={{ marginBottom: "1rem", fontSize: "0.85rem" }}>
          <div style={{ color: "var(--text-muted)", marginBottom: 4 }}>
            <strong style={{ color: "var(--text)" }}>De:</strong> {email.sender}
          </div>
          <div style={{ color: "var(--text-muted)", marginBottom: 10 }}>
            <strong style={{ color: "var(--text)" }}>Asunto:</strong> {email.subject}
          </div>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button type="button" className="btn-secondary" onClick={() => setShowEmailBody((v) => !v)}>
              {showEmailBody ? "Ocultar email" : "Ver email completo"}
            </button>
            {gmailUrl && (
              <a href={gmailUrl} target="_blank" rel="noopener noreferrer" className="btn-secondary" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center" }}>
                Abrir en Gmail ↗
              </a>
            )}
          </div>

          {showEmailBody && (
            <iframe
              srcDoc={email.body_html}
              sandbox=""
              style={{
                width: "100%",
                height: 400,
                border: "1px solid var(--border)",
                borderRadius: 6,
                background: "white",
                marginTop: "0.75rem",
              }}
              title="Email preview"
            />
          )}
        </div>
      )}

      {banner && (
        <div style={{ background: "var(--green)", color: "white", padding: "0.5rem 0.75rem", borderRadius: 6, marginBottom: "1rem", fontSize: "0.85rem" }}>
          {banner}
        </div>
      )}
      {error && (
        <div style={{ background: "var(--red)", color: "white", padding: "0.5rem 0.75rem", borderRadius: 6, marginBottom: "1rem", fontSize: "0.85rem" }}>
          {error}
        </div>
      )}

      <div className="card">
        <div className="form-group">
          <label>Monto (CLP)</label>
          <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
        </div>

        <div style={{ display: "flex", gap: "1rem" }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Fecha</label>
            <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Cuenta</label>
            <select value={form.account_id} onChange={(e) => setForm({ ...form, account_id: e.target.value })}>
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
            <select value={selectedBudgetId} onChange={(e) => handleBudgetChange(e.target.value)}>
              <option value="">— Seleccionar —</option>
              {budgets.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
            <label style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6, fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <input type="checkbox" checked={rememberBudget} onChange={(e) => setRememberBudget(e.target.checked)} style={{ width: "auto" }} />
              Recordar para "{form.counterpart}"
            </label>
          </div>
        )}

        <div className="form-group">
          <label>Categoría (opcional)</label>
          <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
            <option value="">— Sin categoría —</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6, fontSize: "0.85rem", color: "var(--text-muted)" }}>
            <input type="checkbox" checked={rememberCat} onChange={(e) => setRememberCat(e.target.checked)} style={{ width: "auto" }} />
            Recordar para "{form.counterpart}"
          </label>
        </div>

        <div className="form-group">
          <label>Comentario</label>
          <textarea value={form.comment} onChange={(e) => setForm({ ...form, comment: e.target.value })} rows={2} />
        </div>

        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem", flexWrap: "wrap" }}>
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

        {/* Auto-confirm: aparece siempre que estén los datos necesarios. */}
        <div style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--border)" }}>
          {autoConfirm ? (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                Futuras transacciones de <strong>{form.counterpart}</strong> se confirmarán automáticamente.
              </div>
              <button className="btn-secondary" onClick={handleDisableAutoConfirm}>
                Desactivar auto
              </button>
            </div>
          ) : (
            <div>
              <button
                className="btn-secondary"
                onClick={handleEnableAutoConfirm}
                disabled={!canEnableAutoConfirm}
                title={!canEnableAutoConfirm ? "Primero asigná categoría y presupuesto" : ""}
                style={{ width: "100%" }}
              >
                Aceptar automáticamente "{form.counterpart}"
              </button>
              {!canEnableAutoConfirm && (
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 6 }}>
                  {isExpense
                    ? "Asigná categoría y presupuesto para activar."
                    : "Asigná categoría para activar."}
                </p>
              )}
              {canEnableAutoConfirm && (
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 6 }}>
                  Confirma esta transacción y todas las futuras con la misma contraparte.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
