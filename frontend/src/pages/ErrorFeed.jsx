import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function ErrorFeed() {
  const [errors, setErrors] = useState([]);

  useEffect(() => {
    api.getErrorEmails().then(setErrors);
  }, []);

  return (
    <div style={{ maxWidth: 700 }}>
      <h1 style={{ marginBottom: "1rem" }}>Errores de parseo</h1>

      {errors.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>No hay emails con errores pendientes.</p>
      ) : (
        errors.map((e) => (
          <Link
            to={`/errors/${e.id}`}
            key={e.id}
            className="card"
            style={{
              display: "block",
              marginBottom: "0.5rem",
              textDecoration: "none",
              color: "inherit",
            }}
          >
            <div style={{ fontWeight: 500 }}>{e.subject}</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              {e.sender} · {new Date(e.received_at).toLocaleDateString("es-CL")}
            </div>
          </Link>
        ))
      )}
    </div>
  );
}
