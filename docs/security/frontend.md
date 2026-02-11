# Frontend security design

This document describes the security architecture of the h4ckath0n frontend template.

## Device key model

Each browser device generates a P 256 ECDSA keypair on first use:

- **Private key**: generated with `crypto.subtle.generateKey` as non extractable. Stored in IndexedDB
  via `idb-keyval` so the browser cannot export it to JavaScript.
- **Public key**: exported as JWK and registered with the backend. The server associates it with a
  `device_id` (d prefix) and `user_id` (u prefix).

### Threat model

| Threat | Mitigation |
|---|---|
| XSS exfiltrating device key | The private key is non extractable, so it cannot be exported |
| XSS minting tokens | An attacker can call `crypto.subtle.sign` while the page is open. CSP and XSS prevention reduce this risk. |
| IndexedDB cleared | The device key is regenerated and must be rebound on next login |
| Device theft | Device key is bound to the browser profile. OS level lock and passkey user verification add protection. |

### Why non extractable

The `extractable: false` parameter means the private key exists only inside the browser crypto
subsystem. Even with full DOM access, an attacker cannot serialize or transmit the key. They can
only sign while the page is open, limiting the window of abuse.

## JWT structure

The client mints short lived JWTs signed with the device private key (ES256).

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

### Mandatory `aud` claim (usage bound tokens)

The `aud` claim is required and binds the token to a channel:

| Channel | `aud` value |
|---|---|
| HTTP REST | `h4ckath0n:http` |
| WebSocket | `h4ckath0n:ws` |
| SSE | `h4ckath0n:sse` |

The client mints a separate token per channel by setting the correct `aud`. The server enforces
that `aud` matches the expected channel and rejects missing or mismatched values. This prevents
cross channel token reuse.

### What is not in the JWT

The JWT contains no privilege claims. There is no role, scope, or permission data in the token.
The server loads the user record from the database and enforces authorization from there.

## Token lifecycle (template default)

- Tokens are held in memory only. They are never written to localStorage, sessionStorage, or cookies.
- The web template uses a 15 minute lifetime with a 60 second renewal buffer.
- When the cached token is expired or missing, a new one is minted automatically.
- On 401 responses, the token cache is cleared. No automatic redirect is triggered.

## Server verification

The backend verifies each request as follows:

1. Extract JWT from `Authorization: Bearer <token>` (HTTP and SSE) or `?token=` (WebSocket).
2. Read `kid` from the JWT header and load the device record.
3. Load the device public key and verify the signature (ES256).
4. Validate `exp` and parse `iat` using PyJWT.
5. Validate `aud` matches the expected channel.
6. Reject revoked devices.
7. Load the user from the device binding and enforce RBAC from the database.

The server does not read roles or scopes from the JWT.

## API client

All authenticated requests go through the `openapi-fetch` client in `src/api/client.ts`.

- It mints or reuses the in memory JWT.
- It sets the `Authorization` header for every request.
- It clears the cached token on 401 responses.

Unauthenticated endpoints use direct `fetch` calls without the auth header.

## Content Security Policy

The backend template ships CSP headers via middleware.

### Production

```
default-src 'self';
script-src 'self';
style-src 'self';
img-src 'self' data:;
font-src 'self';
connect-src 'self' wss:;
frame-ancestors 'none';
base-uri 'self';
form-action 'self'
```

### Development

```
default-src 'self' http://localhost:*;
script-src 'self' http://localhost:*;
style-src 'self' 'unsafe-inline' http://localhost:*;
img-src 'self' data: http://localhost:*;
font-src 'self' http://localhost:*;
connect-src 'self' http://localhost:* ws://localhost:*;
frame-ancestors 'none';
base-uri 'self';
form-action 'self'
```

`unsafe-inline` is allowed for styles only in development because Vite injects style tags. WebSocket
connections to `localhost` are allowed for the dev server.

## WebSocket auth

WebSocket connections authenticate via a `token` query parameter because the browser WebSocket API
cannot set custom headers:

1. The client mints a device JWT with `aud: "h4ckath0n:ws"`.
2. It opens a WebSocket: `ws://host/path?token=<jwt>`.
3. The server extracts the token, verifies the signature, checks `aud`, and loads the user.
4. If invalid, the server accepts and immediately closes with code 1008.
5. If valid, the server accepts and sends a welcome message.

## SSE auth

SSE endpoints authenticate via the `Authorization: Bearer <jwt>` header. The template uses
`@microsoft/fetch-event-source` because the native `EventSource` API does not support custom
headers.

1. The client mints a device JWT with `aud: "h4ckath0n:sse"`.
2. It calls `fetchEventSource("/path", { headers: { Authorization: "Bearer <jwt>" } })`.
3. The server verifies `aud = h4ckath0n:sse` and streams events if authorized, or returns 401.
4. The server allows a `?token=` query parameter for manual debugging only.

## WebAuthn security

- Challenge state is stored server side with a default TTL of 300 seconds.
- Challenges are single use and consumed on successful completion.
- The browser `credentialId` (base64url) is stored separately from the internal passkey ID (k prefix).
- WebAuthn payloads, assertions, and attestation objects should never be logged.
- Origin and RP ID are validated strictly in production mode.

## Passkey management

- Users can register multiple passkeys.
- The last active passkey cannot be revoked (LAST_PASSKEY invariant).
- Revoked passkeys have `revoked_at` set and cannot be un revoked.
