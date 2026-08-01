import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../state/auth";
import { useStatusLiveSocket } from "../api/ws";

export function Layout() {
  const user = useAuth((s) => s.user);
  const logout = useAuth((s) => s.logout);
  const { connected } = useStatusLiveSocket();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>CCMS</h1>
        <nav>
          <NavLink to="/summary" className={({ isActive }) => (isActive ? "active" : undefined)}>
            Summary
          </NavLink>
          <NavLink to="/devices" className={({ isActive }) => (isActive ? "active" : undefined)}>
            Devices
          </NavLink>
          <NavLink to="/alerts" className={({ isActive }) => (isActive ? "active" : undefined)}>
            Alerts
          </NavLink>
          <NavLink to="/reports" className={({ isActive }) => (isActive ? "active" : undefined)}>
            Reports
          </NavLink>
          {user?.role === "admin" && (
            <NavLink to="/admin" className={({ isActive }) => (isActive ? "active" : undefined)}>
              Admin
            </NavLink>
          )}
        </nav>
        <div className="ws-status">
          <div style={{ marginBottom: 6 }}>
            <span className={`state-dot ${connected ? "state-UP" : "state-DOWN"}`} />
            {connected ? "Live" : "Reconnecting..."}
          </div>
          {user && (
            <div>
              {user.name}
              <br />
              <button
                onClick={logout}
                style={{ background: "none", border: "none", padding: 0, color: "var(--accent)", fontSize: 12 }}
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </aside>
      <div className="main">
        <Outlet />
      </div>
    </div>
  );
}
