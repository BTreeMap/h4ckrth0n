# Architecture overview

This document describes the core request flow and module boundaries in h4ckath0n.

## Application factory

`h4ckath0n.create_app()` builds a FastAPI application with these defaults:

- Registers the passkey routers at `/auth/passkey` and `/auth/passkeys`.
- Optionally registers password routes when the password extra is installed and enabled.
- Creates a SQLAlchemy engine from `Settings.database_url`.
- Calls `Base.metadata.create_all()` to create tables on startup.
- Stores `settings`, `engine`, and `session_factory` on `app.state`.

The factory also mounts basic routes:

- `GET /` returns a welcome message.
- `GET /health` returns a simple health status.

## Request flow

### Passkey registration

1. Client calls `POST /auth/passkey/register/start` to get a flow id and WebAuthn options.
2. Browser runs `navigator.credentials.create()`.
3. Client submits `POST /auth/passkey/register/finish` with the WebAuthn credential.
4. Server verifies the attestation, stores the credential, and binds a device key if provided.

### Passkey login

1. Client calls `POST /auth/passkey/login/start` to get a flow id and options.
2. Browser runs `navigator.credentials.get()`.
3. Client submits `POST /auth/passkey/login/finish` with the WebAuthn assertion.
4. Server verifies the assertion, updates sign counters, and binds a device key if provided.

### Device JWT authentication

After login, the client mints ES256 JWTs signed by the device private key. The server validates the
JWT in `h4ckath0n.realtime.auth.verify_device_jwt` and loads the user from the database.

## Data model

The auth tables live in `h4ckath0n.auth.models`:

- `User` stores role and scopes.
- `WebAuthnCredential` stores passkey public keys.
- `WebAuthnChallenge` stores single use WebAuthn challenges.
- `Device` stores device public keys for JWT verification.
- `PasswordResetToken` stores password reset tokens when password auth is enabled.

## Template API

The full stack template mounts its own demo routes in `app.main` and uses the same auth and realtime
helpers from the library. The template also sets a Content Security Policy via middleware.
