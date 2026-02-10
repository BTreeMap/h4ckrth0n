# Passkeys (WebAuthn) – Architecture and Deployment Guide

h4ckath0n uses **passkeys** (WebAuthn / FIDO2) as the default authentication
method. This document covers the threat model, invariants, deployment settings,
and recovery guidance.

## Threat model

### What passkeys protect against

| Threat | Mitigation |
|---|---|
| Phishing | Credentials are bound to the relying party (RP) origin. |
| Credential stuffing | No reusable passwords to stuff. |
| Server-side credential theft | Only public keys stored server-side; private keys never leave the authenticator. |
| Replay attacks | Each ceremony uses a random, single-use, time-limited challenge. |
| Session hijacking | Device-signed short-lived JWTs held in memory only; no persistent tokens to steal. |

### Trust boundaries

- **Authenticator** (hardware key, platform biometric): stores private key material.
- **Browser**: mediates WebAuthn API calls, enforces origin checks.
- **Server** (h4ckath0n): stores public keys, validates attestation/assertion,
  verifies device-signed ES256 JWTs, enforces authorization from DB.

### What passkeys do NOT protect against

- Compromised device (malware with full OS access).
- Social engineering that convinces users to approve a ceremony on a
  phishing site that proxies requests (mitigated by origin binding, but
  sophisticated real-time phishing proxies exist).
- Loss of all authenticators (recovery discussed below).

## Invariants

### Last-passkey rule

A user **must never become un-loginable**. If a passkey is the user's last
active (non-revoked) credential, the system blocks revocation and returns:

```json
{
  "detail": {
    "code": "LAST_PASSKEY",
    "message": "Cannot revoke the last active passkey."
  }
}
```

This check is enforced **transactionally**: in Postgres, a `SELECT ... FOR
UPDATE` lock on the user's credentials prevents two concurrent revoke requests
from both succeeding.

### Challenge lifecycle

| Property | Value |
|---|---|
| Storage | Server-side (`webauthn_challenges` table) |
| TTL | Default 300 seconds (`H4CKATH0N_WEBAUTHN_TTL_SECONDS`) |
| Single-use | `consumed_at` set on successful finish; replays rejected |
| Cleanup | `cleanup_expired_challenges()` deletes expired rows |

### Credential storage

| Field | Purpose |
|---|---|
| `id` | Internal key ID (`k...`, 32 chars) – used in URLs and logs |
| `credential_id` | Browser's credential ID (base64url) – used for signature verification |
| `public_key` | COSE public key bytes – used by py_webauthn for verification |
| `sign_count` | Monotonic counter – updated on each login |

The internal `id` (`k...`) is **not** the same as the browser's `credentialId`.
This separation allows safe logging and URL use of the internal ID without
exposing cryptographic material.

## Deployment settings

### Required in production

| Variable | Example | Description |
|---|---|---|
| `H4CKATH0N_RP_ID` | `example.com` | WebAuthn relying party ID (typically the domain) |
| `H4CKATH0N_ORIGIN` | `https://example.com` | Expected origin (scheme + host + optional port) |
| `H4CKATH0N_ENV` | `production` | Enables strict validation |

### Development defaults

In `development` mode (default), h4ckath0n uses safe localhost defaults:

- `rp_id`: `localhost`
- `origin`: `http://localhost:8000`

Warnings are emitted for each defaulted value.

### Optional settings

| Variable | Default | Description |
|---|---|---|
| `H4CKATH0N_WEBAUTHN_TTL_SECONDS` | `300` | Challenge expiry (seconds) |
| `H4CKATH0N_USER_VERIFICATION` | `preferred` | WebAuthn UV requirement |
| `H4CKATH0N_ATTESTATION` | `none` | Attestation conveyance preference |
| `H4CKATH0N_PASSWORD_AUTH_ENABLED` | `false` | Enable password routes (requires `[password]` extra) |

## Credential lifecycle

### Registration (account creation)

```
Browser                          Server
   |                                |
   |  POST /auth/passkey/register/start
   |  <--- flow_id + options -------|  (user created, challenge stored)
   |                                |
   |  navigator.credentials.create()
   |  (user approves biometric/PIN) |
   |                                |
   |  POST /auth/passkey/register/finish
   |  ---> flow_id + credential + device_public_key_jwk
   |  <--- user_id + device_id -----|  (verify attestation, store credential, bind device)
```

### Login (username-less)

```
Browser                          Server
   |                                |
   |  POST /auth/passkey/login/start
   |  <--- flow_id + options -------|  (challenge stored, no allowCredentials)
   |                                |
   |  navigator.credentials.get()
   |  (user selects passkey)        |
   |                                |
   |  POST /auth/passkey/login/finish
   |  ---> flow_id + credential + device_public_key_jwk
   |  <--- user_id + device_id -----|  (verify assertion, update sign_count, bind device)
```

### Adding a second passkey

Authenticated users should add a second passkey early as a recovery mechanism.

```
POST /auth/passkey/add/start   (with device-signed Bearer JWT)
POST /auth/passkey/add/finish  (with device-signed Bearer JWT)
```

The `excludeCredentials` list prevents re-registering the same authenticator.

### Revocation

```
POST /auth/passkeys/{key_id}/revoke  (with device-signed Bearer JWT)
```

Sets `revoked_at` on the credential. Blocked if it's the last active passkey.

## Multiple passkeys and recovery

### Recommended setup

1. Register a primary passkey (e.g., platform authenticator / biometric).
2. Add a second passkey (e.g., security key or another device).
3. Store the second authenticator safely as a recovery option.

### Recovery when all passkeys are lost

Without any active passkeys, the user cannot log in. Recovery options:

1. **If email extra is enabled** (`h4ckath0n[email]`): admin-initiated recovery
   flow that verifies email ownership and allows registering a new passkey.
2. **Admin intervention**: an admin can create a recovery flow for the user.
3. **Out-of-band verification**: identity verification + admin provisioning.

The library intentionally does not provide automatic recovery to prevent
social engineering attacks.

## Optional password auth

Password auth is available as an optional extra:

```bash
pip install "h4ckath0n[password]"
```

And must be explicitly enabled:

```
H4CKATH0N_PASSWORD_AUTH_ENABLED=true
```

When enabled, password routes (`/auth/register`, `/auth/login`,
`/auth/password-reset/*`) are mounted alongside passkey routes.

Password auth is an **identity bootstrap method** only: it proves who the user
is so a device key can be bound.  After binding, all API calls use the same
device-signed ES256 JWT flow.  Password endpoints never return access tokens,
refresh tokens, or session cookies.

## Database considerations

### Indexes

The following indexes are created automatically:

- `webauthn_credentials.user_id` – fast lookup by user
- `webauthn_credentials.credential_id` – unique, fast lookup by browser credential
- `webauthn_challenges.expires_at` – efficient cleanup queries

### Cleanup

Call `cleanup_expired_challenges(db_session)` periodically to remove expired
challenge rows. This can be triggered by a cron job, background task, or
startup hook.

### Postgres recommendations

- Use `postgresql+psycopg://` connection string (psycopg 3 binary included).
- Ensure `H4CKATH0N_RP_ID` and `H4CKATH0N_ORIGIN` are set for production.
- The `SELECT ... FOR UPDATE` locking for the last-passkey invariant requires
  a proper transaction-capable database (Postgres). SQLite works for
  development but does not support row-level locking.
