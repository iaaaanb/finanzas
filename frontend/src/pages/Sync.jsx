import { useEffect, useState, useCallback } from "react";
import { api } from "../api";
import { useRefresh } from "../components/RefreshContext";

const TRIGGER_LABELS = {
  CRON: "Automático",
  UI_INCREMENTAL: "Manual",
  UI_BACKFILL: "Backfill",
};

const STATUS_COLORS = {
  RUNNING: "var(--yellow)",
  SUCCESS: "var(--green)",
  FAILED: "var(--red)",
};

function formatRelative(dt) {
  if (!dt) return "—";
  const d = new Date(dt);
  const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diffSec < 60) return `hace ${diffSec}s`;
  if (diffSec < 3600) return `hace ${Math.floor(diffSec / 60)} min`;
  if (diffSec < 86400) return `hace ${Math.floor(diffSec / 3600)} h`;
  return d.toLocaleString("es-CL", { dateStyle: "short", timeStyle: "short" });
}

function formatAbsolute(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("es-CL", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function RunRow({ run }) {
  const duration =
    run.finished_at && run.started_at
      ? Math.round(
          (new Date(run.finished_at).getTime() -
            new Date(run.started_at).getTime()) /
            1000
        )
      : null;

  return (
    <div
      className="card"
      style={{ marginBottom: "0.5rem", fontSize: "0.85rem" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 4,
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            className="badge"
            style={{
              background: STATUS_COLORS[run.status],
              color: run.status === "RUNNING" ? "#000" : "white",
            }}
          >
            {run.status}
          </span>
          <span style={{ color: "var(--text-muted)" }}>
            {TRIGGER_LABELS[run.trigger] || run.trigger}
          </span>
        </span>
        <span style={{ color: "var(--text-muted)" }}>
          {formatAbsolute(run.started_at)}
          {duration !== null && (
            <span style={{ marginLeft: 8 }}>· {duration}s</span>
          )}
        </span>
      </div>

      {run.status !== "RUNNING" && (
        <div style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
          {run.fetched ?? 0} traído{run.fetched === 1 ? "" : "s"} ·{" "}
          <span style={{ color: "var(--green)" }}>{run.parsed ?? 0} parseados</span> ·{" "}
          <span>{run.skipped ?? 0} ignorados</span>
          {(run.parse_errors ?? 0) > 0 && (
            <span style={{ color: "var(--red)" }}>
              {" "}· {run.parse_errors} errores
            </span>
          )}
          {(run.duplicates ?? 0) > 0 && (
            <span> · {run.duplicates} duplicados</span>
          )}
        </div>
      )}

      {run.error_message && (
        <div
          style={{
            marginTop: 6,
            color: "var(--red)",
            fontSize: "0.8rem",
            fontFamily: "monospace",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {run.error_message}
        </div>
      )}
    </div>
  );
}

export default function Sync() {
  const { triggerRefresh } = useRefresh();
  const [status, setStatus] = useState(null);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Default backfill date = hace 7 días
  const [backfillDate, setBackfillDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().split("T")[0];
  });

  const refresh = useCallback(async () => {
    const [s, r] = await Promise.all([
      api.getSyncStatus(),
      api.getSyncRuns(20),
    ]);
    setStatus(s);
    setRuns(r);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Mientras hay un sync corriendo, hacer poll cada 3s para que la UI
  // muestre el resultado ni bien termina sin que el usuario tenga que recargar.
  useEffect(() => {
    if (!status?.active_run) return;
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [status?.active_run, refresh]);

  const handleSync = async (kind) => {
    setLoading(true);
    setError(null);
    try {
      if (kind === "incremental") {
        await api.triggerIncrementalSync();
      } else {
        await api.triggerBackfillSync(backfillDate);
      }
      await refresh();
      // El sidebar muestra saldos y presupuestos, que pueden haber cambiado
      // si el sync confirmó algo (aunque por ahora todo sale como PENDING,
      // refrescamos por las dudas).
      triggerRefresh();
    } catch (e) {
      if (e.status === 409) {
        // Otro sync ya estaba corriendo. Mensaje específico, refrescamos
        // status para que se vea el run activo y arranque el polling.
        setError("Ya hay un sync en progreso. Esperá a que termine.");
        await refresh();
      } else {
        setError(e.message || "Error desconocido");
      }
    } finally {
      setLoading(false);
    }
  };

  const lastRun = status?.last_run;
  const activeRun = status?.active_run;
  const isRunning = !!activeRun || loading;

  return (
    <div style={{ maxWidth: 700 }}>
      <h1 style={{ marginBottom: "1rem" }}>Sincronización</h1>

      {/* Estado actual */}
      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>Última actualización</h3>
        {lastRun ? (
          <div>
            <div style={{ fontSize: "0.9rem" }}>
              {formatRelative(lastRun.finished_at || lastRun.started_at)}
              <span
                className="badge"
                style={{
                  background: STATUS_COLORS[lastRun.status],
                  color: lastRun.status === "RUNNING" ? "#000" : "white",
                  marginLeft: 8,
                }}
              >
                {lastRun.status}
              </span>
            </div>
            {lastRun.status === "SUCCESS" && (
              <div
                style={{
                  fontSize: "0.85rem",
                  color: "var(--text-muted)",
                  marginTop: 4,
                }}
              >
                {lastRun.parsed} transaccion{lastRun.parsed === 1 ? "" : "es"} nueva
                {lastRun.parsed === 1 ? "" : "s"}
                {lastRun.parse_errors > 0 && (
                  <span style={{ color: "var(--red)" }}>
                    {" "}· {lastRun.parse_errors} con error
                  </span>
                )}
              </div>
            )}
          </div>
        ) : (
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
            Nunca se ha sincronizado.
          </p>
        )}
      </div>

      {/* Acciones */}
      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Sincronizar ahora</h3>

        <div style={{ marginBottom: "1rem" }}>
          <button
            className="btn-primary"
            onClick={() => handleSync("incremental")}
            disabled={isRunning}
            style={{ width: "100%" }}
          >
            {isRunning
              ? "Sincronizando..."
              : "Traer emails nuevos"}
          </button>
          <p
            style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              marginTop: 6,
            }}
          >
            Trae todo lo recibido desde el último email registrado.
          </p>
        </div>

        <div
          style={{
            borderTop: "1px solid var(--border)",
            paddingTop: "1rem",
          }}
        >
          <h4 style={{ fontSize: "0.9rem", marginBottom: "0.5rem" }}>
            Backfill desde fecha
          </h4>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <input
              type="date"
              value={backfillDate}
              onChange={(e) => setBackfillDate(e.target.value)}
              max={new Date().toISOString().split("T")[0]}
              disabled={isRunning}
              style={{ flex: 1 }}
            />
            <button
              className="btn-secondary"
              onClick={() => handleSync("backfill")}
              disabled={isRunning || !backfillDate}
            >
              Backfill
            </button>
          </div>
          <p
            style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              marginTop: 6,
            }}
          >
            Trae todos los emails desde esa fecha hasta hoy. Los ya procesados
            se ignoran automáticamente.
          </p>
        </div>
      </div>

      {error && (
        <div
          style={{
            background: "var(--red)",
            color: "white",
            padding: "0.5rem 0.75rem",
            borderRadius: 6,
            marginBottom: "1rem",
            fontSize: "0.85rem",
          }}
        >
          {error}
        </div>
      )}

      {/* Historial */}
      <div>
        <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>Historial</h3>
        {runs.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
            Sin runs todavía.
          </p>
        ) : (
          runs.map((run) => <RunRow key={run.id} run={run} />)
        )}
      </div>
    </div>
  );
}
