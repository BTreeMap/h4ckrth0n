import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Fingerprint, Plus, Trash2, AlertCircle } from "lucide-react";
import { apiFetch } from "../auth";
import { toCreateOptions, serializeCreateResponse } from "../auth/webauthn";
import { Card, CardContent, CardHeader } from "../components/Card";
import { Button } from "../components/Button";
import { Alert } from "../components/Alert";

interface Passkey {
  id: string;
  label: string | null;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export function Settings() {
  const queryClient = useQueryClient();
  const [addLoading, setAddLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPasskeyError, setLastPasskeyError] = useState<string | null>(null);

  const { data: passkeys, isLoading } = useQuery<Passkey[]>({
    queryKey: ["passkeys"],
    queryFn: async () => {
      const res = await apiFetch<{ passkeys: Passkey[] }>("/auth/passkeys");
      if (!res.ok) throw new Error("Failed to load passkeys");
      return res.data.passkeys;
    },
  });

  const revokeMutation = useMutation({
    mutationFn: async (passkeyId: string) => {
      setLastPasskeyError(null);
      const res = await apiFetch(`/auth/passkeys/${passkeyId}/revoke`, {
        method: "POST",
      });
      if (!res.ok) {
        const data = res.data as { error?: string; detail?: string };
        if (data.error === "LAST_PASSKEY" || data.detail?.includes("LAST_PASSKEY")) {
          throw new Error("LAST_PASSKEY");
        }
        throw new Error(data.detail || "Revoke failed");
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["passkeys"] });
    },
    onError: (err: Error) => {
      if (err.message === "LAST_PASSKEY") {
        setLastPasskeyError(
          "Cannot revoke your last active passkey. Add another passkey first to maintain account access."
        );
      } else {
        setError(err.message);
      }
    },
  });

  const handleAddPasskey = async () => {
    setAddLoading(true);
    setError(null);
    try {
      const startRes = await apiFetch<{ options: Record<string, unknown>; flow_id: string }>(
        "/auth/passkey/add/start",
        { method: "POST" }
      );
      if (!startRes.ok) throw new Error("Failed to start passkey addition");

      const createOptions = toCreateOptions(
        startRes.data.options as unknown as Parameters<typeof toCreateOptions>[0]
      );
      const credential = (await navigator.credentials.create(
        createOptions
      )) as PublicKeyCredential | null;
      if (!credential) throw new Error("Passkey creation cancelled");

      const finishRes = await apiFetch("/auth/passkey/add/finish", {
        method: "POST",
        body: JSON.stringify({
          flow_id: startRes.data.flow_id,
          credential: serializeCreateResponse(credential),
        }),
      });
      if (!finishRes.ok) throw new Error("Failed to add passkey");

      queryClient.invalidateQueries({ queryKey: ["passkeys"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add passkey");
    } finally {
      setAddLoading(false);
    }
  };

  const activePasskeys = passkeys?.filter((p) => !p.revoked_at) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">Settings</h1>
        <p className="text-text-muted">Manage your passkeys and account security</p>
      </div>

      {error && <Alert variant="error">{error}</Alert>}
      {lastPasskeyError && (
        <Alert variant="warning">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{lastPasskeyError}</span>
          </div>
        </Alert>
      )}

      <Card>
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Fingerprint className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-text">Passkeys</h2>
            <span className="text-sm text-text-muted">({activePasskeys.length} active)</span>
          </div>
          <Button size="sm" onClick={handleAddPasskey} disabled={addLoading}>
            <Plus className="w-4 h-4" />
            {addLoading ? "Adding..." : "Add Passkey"}
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-primary border-t-transparent" />
            </div>
          ) : passkeys && passkeys.length > 0 ? (
            <div className="divide-y divide-border">
              {passkeys.map((passkey) => (
                <div key={passkey.id} className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-text">
                      {passkey.label || "Unnamed passkey"}
                      {passkey.revoked_at && (
                        <span className="ml-2 text-xs text-danger">(revoked)</span>
                      )}
                    </p>
                    <p className="text-xs text-text-muted font-mono">{passkey.id}</p>
                    <p className="text-xs text-text-muted">
                      Created: {new Date(passkey.created_at).toLocaleDateString()}
                      {passkey.last_used_at && (
                        <> | Last used: {new Date(passkey.last_used_at).toLocaleDateString()}</>
                      )}
                    </p>
                  </div>
                  {!passkey.revoked_at && (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => revokeMutation.mutate(passkey.id)}
                      disabled={revokeMutation.isPending}
                    >
                      <Trash2 className="w-3 h-3" />
                      Revoke
                    </Button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted py-4 text-center">No passkeys found.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
