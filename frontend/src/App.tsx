import { useEffect, useState } from "react";
import { api, getToken, setToken, clearToken } from "./api";
import Login from "./pages/Login";
import Today from "./pages/Today";
import Progress from "./pages/Progress";
import Setup from "./pages/Setup";

type Tab = "today" | "progress" | "goals";

const TABS: { id: Tab; icon: string; label: string }[] = [
  { id: "today", icon: "🏠", label: "Today" },
  { id: "progress", icon: "📈", label: "Progress" },
  { id: "goals", icon: "🎯", label: "Goals" },
];

export default function App() {
  const [authed, setAuthed] = useState<boolean>(!!getToken());
  const [tab, setTab] = useState<Tab>("today");

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

  if (!authed) {
    return (
      <div className="app">
        <header className="topbar">
          <h1>ripe<span className="accent">_fitness</span></h1>
        </header>
        <main>
          <Login onLogin={handleLogin} />
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>ripe<span className="accent">_fitness</span></h1>
        <button className="ghost small" onClick={handleLogout}>Log out</button>
      </header>

      <main className="with-nav">
        {tab === "today" && <Today />}
        {tab === "progress" && <Progress />}
        {tab === "goals" && <Setup />}
      </main>

      <nav className="bottom-nav">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "active" : ""}
            onClick={() => setTab(t.id)}
          >
            <span className="nav-icon">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
