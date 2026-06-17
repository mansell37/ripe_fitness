import { useState } from "react";

interface Props {
  onLogin: (username: string, password: string) => Promise<void>;
  onRegister: (username: string, password: string) => Promise<void>;
}

export default function Login({ onLogin, onRegister }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (mode === "login") await onLogin(username, password);
      else await onRegister(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const isRegister = mode === "register";

  return (
    <div className="card centered">
      <h2>{isRegister ? "Create account" : "Sign in"}</h2>
      <p className="muted">
        {isRegister
          ? "Pick a username and password to start training."
          : "Welcome back — log in to your coach."}
      </p>
      <form onSubmit={submit}>
        <input
          type="text"
          placeholder="Username"
          value={username}
          autoCapitalize="none"
          autoCorrect="off"
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <input
          type="password"
          placeholder={isRegister ? "Password (8+ characters)" : "Password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" disabled={loading || !username || !password}>
          {loading ? "…" : isRegister ? "Create account" : "Sign in"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      <p className="muted small" style={{ marginTop: 14 }}>
        {isRegister ? "Already have an account?" : "New here?"}{" "}
        <button
          className="linklike"
          onClick={() => {
            setMode(isRegister ? "login" : "register");
            setError(null);
          }}
        >
          {isRegister ? "Sign in" : "Create one"}
        </button>
      </p>
    </div>
  );
}
