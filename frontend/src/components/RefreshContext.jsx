import { createContext, useContext, useState, useCallback } from "react";

const RefreshContext = createContext();

export function RefreshProvider({ children }) {
  const [key, setKey] = useState(0);
  const triggerRefresh = useCallback(() => setKey((k) => k + 1), []);
  return (
    <RefreshContext.Provider value={{ key, triggerRefresh }}>
      {children}
    </RefreshContext.Provider>
  );
}

export function useRefresh() {
  return useContext(RefreshContext);
}
