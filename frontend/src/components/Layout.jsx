import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(
    typeof window !== "undefined" ? window.innerWidth < 768 : false
  );
  const location = useLocation();

  // Mantener isMobile sincronizado con el viewport. 768px es el breakpoint
  // estándar al que rompen la mayoría de los layouts mobile.
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // Cerrar el sidebar al navegar (típico pattern mobile). El usuario toca un
  // link en el sidebar → navegamos → sidebar se cierra automáticamente.
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div style={{ display: "flex", minHeight: "100vh", position: "relative" }}>
      {/* Botón hamburguesa — solo visible en mobile, y solo si el sidebar está cerrado */}
      {isMobile && !sidebarOpen && (
        <button
          onClick={() => setSidebarOpen(true)}
          aria-label="Abrir menú"
          style={{
            position: "fixed",
            top: 12,
            left: 12,
            zIndex: 30,
            width: 40,
            height: 40,
            padding: 0,
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
          }}
        >
          <span
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 4,
              width: 18,
            }}
          >
            <span style={{ display: "block", height: 2, background: "var(--text)", borderRadius: 2 }} />
            <span style={{ display: "block", height: 2, background: "var(--text)", borderRadius: 2 }} />
            <span style={{ display: "block", height: 2, background: "var(--text)", borderRadius: 2 }} />
          </span>
        </button>
      )}

      {/* Backdrop oscuro que se ve detrás del sidebar en mobile.
          Al tocarlo, se cierra el sidebar (además del link-navigate). */}
      {isMobile && sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.5)",
            zIndex: 15,
          }}
        />
      )}

      <Sidebar
        isMobile={isMobile}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main
        style={{
          flex: 1,
          padding: isMobile ? "3.5rem 1rem 1rem" : "1.5rem",
          overflowY: "auto",
          minWidth: 0, // evita overflow horizontal por hijos con width grande
        }}
      >
        <Outlet />
      </main>
    </div>
  );
}
