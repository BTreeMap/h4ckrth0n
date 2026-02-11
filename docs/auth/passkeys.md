# Passkeys (WebAuthn)

h4ckath0n uses passkeys as the default authentication method. This document covers the passkey
flows, challenge lifecycle, and data model.

## Routes

Passkey routes are mounted automatically by `create_app()`:

- `POST /auth/passkey/register/start`
- `POST /auth/passkey/register/finish`
- `POST /auth/passkey/login/start`
- `POST /auth/passkey/login/finish`
- `POST /auth/passkey/add/start` (requires device JWT)
- `POST /auth/passkey/add/finish` (requires device JWT)
- `GET /auth/passkeys` (requires device JWT)
- `POST /auth/passkeys/{key_id}/revoke` (requires device JWT)

## Registration flow

1. `register/start` creates a new user and a server side challenge.
2. The browser runs `navigator.credentials.create()` using the returned options.
3. `register/finish` verifies the attestation, stores the credential, and returns a user id and
   device id when a device key is provided.

## Login flow

1. `login/start` creates a server side challenge for a username less login.
2. The browser runs `navigator.credentials.get()`.
3. `login/finish` verifies the assertion, updates the sign counter, and returns a user id and device
   id when a device key is provided.

## Add passkey flow

Authenticated users can add a second passkey using the add start and finish endpoints. The server
builds an `excludeCredentials` list to prevent registering the same authenticator again.

## Challenge lifecycle

Challenges are stored in the `webauthn_challenges` table.

| Property | Value |
|---|---|
| TTL | Default 300 seconds (`H4CKATH0N_WEBAUTHN_TTL_SECONDS`) |
| Single use | `consumed_at` is set on successful finish |
| Cleanup | `cleanup_expired_challenges(db)` deletes expired rows |

## Last passkey invariant

The last active passkey cannot be revoked. The server checks the number of active credentials and
returns the `LAST_PASSKEY` error if a revoke would leave the user without a passkey. In Postgres, the
check uses `SELECT ... FOR UPDATE` for concurrency safety. SQLite ignores the lock, which is
acceptable for development.

## Data model notes

`WebAuthnCredential` stores two identifiers:

- `id`: internal passkey id with a `k` prefix, used in URLs and logs.
- `credential_id`: browser credential id in base64url format, used for verification.

The internal id is separate from the credential id to avoid exposing cryptographic identifiers.

## Production requirements

Passkeys require correct WebAuthn configuration:

- `H4CKATH0N_RP_ID` must match the production domain.
- `H4CKATH0N_ORIGIN` must match the origin, including the scheme.

In development, the settings default to `localhost` and `http://localhost:8000` with warnings.
