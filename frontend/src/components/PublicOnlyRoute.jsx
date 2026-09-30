import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

// Pages like login and signup make no sense for a logged-in user
export default function PublicOnlyRoute() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (isAuthenticated) {
    const destination = location.state?.from?.pathname ?? "/dashboard";
    return <Navigate to={destination} replace />;
  }

  return <Outlet />;
}
