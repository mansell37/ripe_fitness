import { useEffect, useState } from "react";
import { api, getToken, setToken, clearToken } from "./api";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";

export default function App() {
  const [authed, setAuthed] = useState<boolean>(!!getToken());

  // If a stored token is stale, the first authed request will 401 and clear it.
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
          <button className="ghost" onClick={handleLogout}>
            Log out
          </button>
        )}
      </header>
      <main>
        {authed ? <Dashboard /> : <Login onLogin={handleLogin} />}
      </main>
    </div>
  );
}
