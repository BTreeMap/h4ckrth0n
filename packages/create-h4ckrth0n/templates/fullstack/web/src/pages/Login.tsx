import { useState } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setError(null);
    setLoading(true);
    try {
      // Step 1: Begin authentication – get options from server
      const beginRes = await fetch("/api/auth/login/begin", { method: "POST" });
      if (!beginRes.ok) throw new Error("Failed to begin login");
      const options = await beginRes.json();

      // Step 2: Get credential with WebAuthn API
      const credential = await navigator.credentials.get({ publicKey: options });
      if (!credential) throw new Error("Authentication cancelled");

      // Step 3: Finish authentication – send assertion to server
      const finishRes = await fetch("/api/auth/login/finish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credential),
      });
      if (!finishRes.ok) throw new Error("Login failed");
      const data = await finishRes.json();

      await login(data.access_token, data.refresh_token);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-16">
      <h1 className="text-2xl font-bold">Sign in</h1>
      <p className="mt-2 text-sm text-text-muted">
        Authenticate with your passkey.
      </p>
      {error && (
        <p className="mt-4 rounded-md bg-danger/10 p-3 text-sm text-danger">{error}</p>
      )}
      <button
        onClick={() => void handleLogin()}
        disabled={loading}
        className="mt-6 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-50"
      >
        {loading ? "Signing in…" : "Sign in with passkey"}
      </button>
    </div>
  );
}
