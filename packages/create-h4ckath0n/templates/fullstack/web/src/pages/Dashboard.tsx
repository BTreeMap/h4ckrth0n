import { useAuth } from "../auth";
import { Card, CardContent, CardHeader } from "../components/Card";
import { Shield, User, Key } from "lucide-react";

export function Dashboard() {
  const { userId, deviceId, role, displayName } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text" data-testid="dashboard-heading">Dashboard</h1>
        <p className="text-text-muted">
          Welcome{displayName ? `, ${displayName}` : ""}!
        </p>
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="flex items-center gap-3 py-5">
            <div className="p-2 bg-primary/10 rounded-xl">
              <User className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-xs text-text-muted">User ID</p>
              <p className="text-sm font-mono text-text truncate max-w-[160px]">{userId}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 py-5">
            <div className="p-2 bg-primary/10 rounded-xl">
              <Key className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-xs text-text-muted">Device ID</p>
              <p className="text-sm font-mono text-text truncate max-w-[160px]">{deviceId}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 py-5">
            <div className="p-2 bg-primary/10 rounded-xl">
              <Shield className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-xs text-text-muted">Role</p>
              <p className="text-sm font-medium text-text capitalize">{role || "user"}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-text">Getting Started</h2>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-text-muted">
          <p>
            Your device has a unique P-256 keypair stored in IndexedDB. The private key is
            non-extractable and never leaves this browser.
          </p>
          <p>
            API requests are authenticated with short-lived JWTs (15 min) signed by your device
            key. The server verifies each request using your registered public key.
          </p>
          <p>
            Visit <strong>Settings</strong> to manage your passkeys, or start building your app!
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
