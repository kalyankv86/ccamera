import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "../state/auth";
import { Login } from "../pages/Login";
import { Layout } from "../pages/Layout";
import { Summary } from "../pages/Summary";
import { DevicesList } from "../pages/DevicesList";
import { DeviceDetail } from "../pages/DeviceDetail";
import { Alerts } from "../pages/Alerts";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuth((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/summary" replace />} />
        <Route path="summary" element={<Summary />} />
        <Route path="devices" element={<DevicesList />} />
        <Route path="devices/:id" element={<DeviceDetail />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="*" element={<Navigate to="/summary" replace />} />
      </Route>
    </Routes>
  );
}
