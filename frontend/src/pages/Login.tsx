import { useState } from "react";
import { Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth, type CurrentUser } from "../state/auth";

export function Login() {
  const token = useAuth((s) => s.token);
  const setSession = useAuth((s) => s.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (token) return <Navigate to="/summary" replace />;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access_token } = await api.post<{ access_token: string }>("/auth/login", { email, password });
      // Stash immediately so the /auth/me call below is authenticated.
      useAuth.setState({ token: access_token });
      const user = await api.get<CurrentUser>("/auth/me");
      setSession(access_token, user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-box" onSubmit={handleSubmit}>
        <h1>CCMS Login</h1>
        {error && <div className="error-text">{error}</div>}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
