# Frontend Security Design

This document describes the security architecture of the h4ckath0n frontend template.

## Device key model

Each browser/device generates a P-256 ECDSA keypair on first use:

- **Private key**: generated with `crypto.subtle.generateKey` as **non-extractable**. Stored in IndexedDB via `idb-keyval`. The browser's WebCrypto API ensures the key material cannot be read by JavaScript.
- **Public key**: exported as JWK and registered with the backend. The server associates it with a `device_id` (d...) and `user_id` (u...).

### Threat model

| Threat | Mitigation |
|---|---|
| XSS exfiltrating device key | Private key is non-extractable; XSS cannot export it |
| XSS minting tokens | An attacker with XSS can call `crypto.subtle.sign` using the stored key. CSP and standard XSS prevention reduce this risk. |
| IndexedDB cleared | User must re-register a device key on next visit. Passkeys remain valid. |
| Device theft | Device key is bound to the browser profile. OS-level device lock and passkey user verification provide additional protection. |

### Why non-extractable

The `extractable: false` parameter in `generateKey` means the private key exists only inside the browser's crypto subsystem. Even with full DOM access, an attacker cannot serialize or transmit the key. They can only sign while the page is open, limiting the window of abuse.

## JWT structure

The client mints short-lived JWTs signed with the device private key (ES256).

### Header

```json
{
  "alg": "ES256",
  "typ": "JWT",
  "kid": "<device_id d...>"
}
```

### Payload

```json
{
  "sub": "<user_id u...>",
  "iat": 1700000000,
  "exp": 1700000900,
  "aud": "h4ckath0n:http"
}
```

### Mandatory `aud` claim (usage-bound tokens)

The `aud` claim is **mandatory** and binds the token to a specific channel:

| Channel | `aud` value |
|---|---|
| HTTP REST | `h4ckath0n:http` |
| WebSocket | `h4ckath0n:ws` |
| SSE | `h4ckath0n:sse` |

The client mints a separate token per channel by setting the appropriate `aud`. The server enforces the expected `aud` for each route/protocol and rejects tokens with a missing or mismatched `aud`. This prevents cross-channel token reuse (e.g., an HTTP token cannot be used to authenticate a WebSocket connection).

Optional claims:
- `jti`: random nonce for debugging or future audit

### What is NOT in the JWT

The JWT contains **no privilege claims**: no role, no scopes, no permissions. All authorization decisions are made server-side by loading the user record from the database. Even if a client adds extra claims, the server ignores them.

## Token lifecycle

- Tokens are held **in memory only**. They are never written to `localStorage`, `sessionStorage`, or cookies.
- A cached token is reused until it is within 60 seconds of expiry.
- When the cached token expires or is missing, a new one is minted automatically by `getOrMintToken()`.
- On 401 response from the server, the cached token is cleared and the user is redirected to login.
- Tokens have a 15-minute lifetime (900 seconds).

## Server verification

The backend verifies each request as follows:

1. Extract JWT from `Authorization: Bearer <token>` header (HTTP/SSE) or `?token=` query param (WebSocket).
2. Read `kid` from the JWT header to find the device record.
3. Load the device's public key from the database.
4. Verify the JWT signature (ES256) using the public key.
5. Check `exp` and `iat` with a small clock skew allowance.
6. **Validate `aud`** matches the expected channel (`h4ckath0n:http`, `h4ckath0n:ws`, or `h4ckath0n:sse`). Reject if missing or mismatched.
7. Confirm the device is not revoked.
8. Load the user from the device's `user_id` binding.
9. Enforce RBAC and scopes from the user's database record.

The server never trusts any claims about roles or permissions from the JWT.

## API client (`apiFetch`)

All backend requests go through a single `apiFetch` wrapper:

- Automatically mints or reuses the in-memory JWT.
- Sets the `Authorization` header.
- On 401: clears local auth state and redirects to login.
- Never logs the `Authorization` header, tokens, or WebAuthn payloads.
- Unauthenticated endpoints (register/login start/finish) use `publicFetch` which skips the auth header.

## Content Security Policy

The backend template ships CSP headers via middleware:

### Production

```
default-src 'self';
script-src 'self';
style-src 'self';
img-src 'self' data:;
font-src 'self';
connect-src 'self';
frame-ancestors 'none';
base-uri 'self';
form-action 'self'
```

No `unsafe-inline` or `unsafe-eval`. The frontend does not use inline scripts.

### Development

```
default-src 'self' http://localhost:*;
script-src 'self' http://localhost:*;
style-src 'self' 'unsafe-inline' http://localhost:*;
connect-src 'self' http://localhost:* ws://localhost:*;
```

`unsafe-inline` is allowed for styles only in development because Vite's HMR injects style tags. WebSocket connections to `localhost` are allowed for Vite's dev server.

## WebSocket auth

WebSocket connections authenticate via a `token` query parameter because the browser WebSocket API does not support custom headers:

1. The client mints a device JWT with `aud: "h4ckath0n:ws"`.
2. Opens a WebSocket: `ws://host/path?token=<jwt>`.
3. The server extracts the token from the query string, verifies the signature, checks `aud = h4ckath0n:ws`, and loads the user.
4. If invalid, the server accepts the connection and immediately closes with code 1008 (Policy Violation).
5. If valid, the server accepts and sends a welcome message.
6. On token renewal, the client can send a re-auth message on the same connection.

The JWT for WebSocket connections uses `aud: "h4ckath0n:ws"` to prevent cross-channel token reuse.

## SSE auth

SSE endpoints authenticate via the `Authorization: Bearer <jwt>` header (the same as HTTP). The `@microsoft/fetch-event-source` library is used on the client side because the native `EventSource` API does not support custom headers.

1. The client mints a device JWT with `aud: "h4ckath0n:sse"`.
2. Calls `fetchEventSource("/path", { headers: { Authorization: "Bearer <jwt>" } })`.
3. The server verifies `aud = h4ckath0n:sse` and streams events if authorized, or returns 401 if not.

## WebAuthn security

- Challenge state is stored server-side with a default TTL of 300 seconds.
- Challenges are single-use and consumed on successful completion.
- The browser's `credentialId` (base64url) is stored separately from the internal passkey ID (k...).
- WebAuthn payloads, assertions, and attestation objects are never logged.
- Origin and RP ID are validated strictly in production mode.

## Passkey management

- Users can register multiple passkeys.
- The last active (non-revoked) passkey cannot be revoked (LAST_PASSKEY invariant).
- The frontend displays a clear warning when a revoke attempt is blocked.
- Revoked passkeys have `revoked_at` set and can never be un-revoked.
