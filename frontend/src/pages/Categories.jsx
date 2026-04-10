import { useEffect, useState } from "react";
import { api } from "../api";

export default function Categories() {
  const [categories, setCategories] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", color: "#3b82f6" });
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", color: "" });

  const load = () => api.getCategories().then(setCategories);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    await api.createCategory(form);
    setForm({ name: "", color: "#3b82f6" });
    setShowForm(false);
    load();
  };

  const startEdit = (c) => {
    setEditingId(c.id);
    setEditForm({ name: c.name, color: c.color });
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    await api.updateCategory(editingId, editForm);
    setEditingId(null);
    load();
  };

  const handleDelete = async (id) => {
    if (!confirm("¿Eliminar esta categoría?")) return;
    await api.deleteCategory(id);
    load();
  };

  return (
    <div style={{ maxWidth: 500 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h1>Categorías</h1>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancelar" : "+ Nueva"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="card" style={{ marginBottom: "1rem" }}>
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "end" }}>
            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label>Nombre</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="form-group" style={{ width: 60, marginBottom: 0 }}>
              <label>Color</label>
              <input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
            </div>
            <button type="submit" className="btn-primary">Crear</button>
          </div>
        </form>
      )}

      {categories.map((c) => (
        <div key={c.id} className="card" style={{ marginBottom: "0.5rem" }}>
          {editingId === c.id ? (
            <form onSubmit={handleUpdate} style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
              <input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} required style={{ flex: 1 }} />
              <input type="color" value={editForm.color} onChange={(e) => setEditForm({ ...editForm, color: e.target.value })} style={{ width: 40 }} />
              <button type="submit" className="btn-primary">OK</button>
              <button type="button" className="btn-secondary" onClick={() => setEditingId(null)}>✕</button>
            </form>
          ) : (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 12, height: 12, borderRadius: "50%", background: c.color }} />
                {c.name}
              </span>
              <span style={{ display: "flex", gap: "0.5rem" }}>
                <button className="btn-secondary" onClick={() => startEdit(c)}>Editar</button>
                <button className="btn-danger" onClick={() => handleDelete(c.id)}>Eliminar</button>
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
