import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Layout() {
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <>
      <header className="navbar">
        <Link to="/" className="brand">
          PDF Chat
        </Link>
        <nav className="nav-links">
          {isAuthenticated ? (
            <>
              <NavLink to="/dashboard">Dashboard</NavLink>
              <NavLink to="/profile">{user ? user.name : "Profile"}</NavLink>
              {/* Arrow function: onClick={logout} would pass the click event as the reason */}
              <button type="button" className="btn-link" onClick={() => logout()}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Log in</NavLink>
              <NavLink to="/signup">Sign up</NavLink>
            </>
          )}
        </nav>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}
