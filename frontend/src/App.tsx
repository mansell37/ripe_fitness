import { useEffect, useState } from "react";
import { api, getToken, setToken, clearToken } from "./api";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Setup from "./pages/Setup";

type Tab = "plan" | "setup";

export default function App() {
  const [authed, setAuthed] = useState<boolean>(!!getToken());
  const [tab, setTab] = useState<Tab>("plan");

  useEffect(() => {
    if (getToken()) {
      api.getProfile().catch(() => {
        clearToken();
        setAuthed(false);
      });
    }
  }, []);

  async function handleLogin(password: string) {
    const { token } = await api.login(password);
    setToken(token);
    setAuthed(true);
  }

  function handleLogout() {
    clearToken();
    setAuthed(false);
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>
          ripe<span className="accent">_fitness</span>
        </h1>
        {authed && (
          <div className="topbar-right">
            <nav className="tabs">
              <button
                className={tab === "plan" ? "tab active" : "tab"}
                onClick={() => setTab("plan")}
              >
                This week
              </button>
              <button
                className={tab === "setup" ? "tab active" : "tab"}
                onClick={() => setTab("setup")}
              >
                Setup
              </button>
            </nav>
            <button className="ghost" onClick={handleLogout}>
              Log out
            </button>
          </div>
        )}
      </header>
      <main>
        {!authed && <Login onLogin={handleLogin} />}
        {authed && tab === "plan" && <Dashboard />}
        {authed && tab === "setup" && <Setup />}
      </main>
    </div>
  );
}
