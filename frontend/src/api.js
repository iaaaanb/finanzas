const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // Accounts
  getAccounts: () => request("/accounts"),
  getAccount: (id) => request(`/accounts/${id}`),
  createAccount: (data) =>
    request("/accounts", { method: "POST", body: JSON.stringify(data) }),
  updateAccount: (id, data) =>
    request(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  // Categories
  getCategories: () => request("/categories"),
  getCategory: (id) => request(`/categories/${id}`),
  createCategory: (data) =>
    request("/categories", { method: "POST", body: JSON.stringify(data) }),
  updateCategory: (id, data) =>
    request(`/categories/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteCategory: (id) =>
    request(`/categories/${id}`, { method: "DELETE" }),

  // Budgets
  getBudgets: () => request("/budgets"),
  getBudget: (id) => request(`/budgets/${id}`),
  createBudget: (data) =>
    request("/budgets", { method: "POST", body: JSON.stringify(data) }),
  updateBudget: (id, data) =>
    request(`/budgets/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  getBudgetPeriods: (id) => request(`/budgets/${id}/periods`),

  // Transactions
  getTransactions: (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v != null)
    ).toString();
    return request(`/transactions${query ? `?${query}` : ""}`);
  },
  getTransaction: (id) => request(`/transactions/${id}`),
  createTransaction: (data) =>
    request("/transactions", { method: "POST", body: JSON.stringify(data) }),
  updateTransaction: (id, data) =>
    request(`/transactions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  confirmTransaction: (id) =>
    request(`/transactions/${id}/confirm`, { method: "POST" }),

  // Auto-assign rules
  getAutoAssignRules: () => request("/auto-assign-rules"),
  getAutoAssignByCounterpart: (counterpart) =>
    request(`/auto-assign-rules/by-counterpart/${encodeURIComponent(counterpart)}`),

  // Counterparts
  getCounterparts: () => request("/counterparts"),

  // Emails
  getErrorEmails: () => request("/emails/errors"),
  getEmail: (id) => request(`/emails/${id}`),
  resolveEmail: (id, data) =>
    request(`/emails/${id}/resolve`, { method: "POST", body: JSON.stringify(data) }),
};
