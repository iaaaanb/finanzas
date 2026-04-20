import { BrowserRouter, Routes, Route } from "react-router-dom";
import { RefreshProvider } from "./components/RefreshContext";
import Layout from "./components/Layout";
import MainPage from "./pages/MainPage";
import TransactionFeed from "./pages/TransactionFeed";
import TransactionDetail from "./pages/TransactionDetail";
import TransactionCreate from "./pages/TransactionCreate";
import ErrorFeed from "./pages/ErrorFeed";
import Accounts from "./pages/Accounts";
import AccountDetail from "./pages/AccountDetail";
import Categories from "./pages/Categories";
import Budgets from "./pages/Budgets";
import BudgetDetail from "./pages/BudgetDetail";
import ResolveError from "./pages/ResolveError";
import Sync from "./pages/Sync";

export default function App() {
  return (
    <BrowserRouter>
      <RefreshProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<MainPage />} />
            <Route path="/transactions" element={<TransactionFeed />} />
            <Route path="/transactions/new" element={<TransactionCreate />} />
            <Route path="/transactions/:id" element={<TransactionDetail />} />
            <Route path="/errors" element={<ErrorFeed />} />
            <Route path="/errors/:id" element={<ResolveError />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/accounts/:id" element={<AccountDetail />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/budgets" element={<Budgets />} />
            <Route path="/budgets/:id" element={<BudgetDetail />} />
            <Route path="/sync" element={<Sync />} />
          </Route>
        </Routes>
      </RefreshProvider>
    </BrowserRouter>
  );
}
