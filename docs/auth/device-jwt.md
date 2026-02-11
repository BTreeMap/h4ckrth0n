# Device signed JWTs

After login or registration, the client binds a device public key and mints ES256 JWTs that the
server verifies on every authenticated request.

## Device identity

The web template creates a P 256 keypair in the browser:

- The private key is non extractable and stored in IndexedDB.
- The public key is exported as JWK and registered with `/auth/passkey/*` and password routes.

The backend stores the public key in the `devices` table with a `d` prefixed id.

## JWT claims

The server expects the following fields:

- Header `kid` set to the device id.
- Payload `sub` set to the user id.
- Payload `iat` and `exp` for time based validation.
- Payload `aud` for channel binding.

No privilege data is read from the token. Roles and scopes are loaded from the database.

## Audience binding

The `aud` claim prevents cross channel reuse:

| Channel | Expected `aud` |
|---|---|
| HTTP | `h4ckath0n:http` |
| WebSocket | `h4ckath0n:ws` |
| SSE | `h4ckath0n:sse` |

`verify_device_jwt` rejects missing or mismatched `aud` values.

## Verification flow

`h4ckath0n.realtime.auth.verify_device_jwt` validates tokens in this order:

1. Extract `kid` and load the device record.
2. Reject revoked devices.
3. Load the device public key and verify the ES256 signature.
4. Validate `exp` and parse `iat` using PyJWT.
5. Enforce the expected `aud` value.
6. Load the user record by `sub`.

## Transport helpers

- `authenticate_http_request` expects `Authorization: Bearer <jwt>` and `aud` set to
  `h4ckath0n:http`.
- `authenticate_sse_request` expects `Authorization: Bearer <jwt>` and `aud` set to
  `h4ckath0n:sse`. It falls back to `?token=` for manual debugging.
- `authenticate_websocket` expects a `token` query parameter and `aud` set to `h4ckath0n:ws`.

## Template defaults

The web template uses a 15 minute token lifetime with a 60 second renewal buffer. Tokens are stored
in memory only, while the device id and user id are stored in IndexedDB.
