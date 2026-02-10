import { useAuth } from "../auth/AuthContext";

export function Dashboard() {
  const { user } = useAuth();

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="mt-2 text-text-muted">
        Welcome back, <span className="font-mono text-sm">{user?.id}</span>
      </p>
      <div className="mt-8 rounded-lg border border-border bg-surface-alt p-6">
        <p className="text-sm text-text-muted">
          Role: <span className="font-medium text-text">{user?.role}</span>
        </p>
        <p className="mt-1 text-sm text-text-muted">
          Scopes: <span className="font-medium text-text">{user?.scopes.join(", ") || "none"}</span>
        </p>
      </div>
    </div>
  );
}
