import { Outlet, Link } from "react-router";
import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border bg-surface">
        <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-bold text-primary">
            h4ckrth0n
          </Link>
          <div className="flex items-center gap-4">
            {user ? (
              <>
                <Link to="/dashboard" className="text-sm text-text-muted hover:text-text">
                  Dashboard
                </Link>
                <Link to="/settings" className="text-sm text-text-muted hover:text-text">
                  Settings
                </Link>
                {user.role === "admin" && (
                  <Link to="/admin" className="text-sm text-text-muted hover:text-text">
                    Admin
                  </Link>
                )}
                <button
                  onClick={() => void logout()}
                  className="text-sm text-danger hover:text-danger-hover"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-sm text-text-muted hover:text-text">
                  Login
                </Link>
                <Link
                  to="/register"
                  className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-hover"
                >
                  Register
                </Link>
              </>
            )}
          </div>
        </nav>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
