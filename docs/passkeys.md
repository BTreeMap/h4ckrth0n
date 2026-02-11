# Passkeys (WebAuthn)

This document is a short overview of the passkey model used by h4ckath0n. The detailed
implementation guide lives at `docs/auth/passkeys.md`.

## Quick summary

- Passkeys are the default auth method and use WebAuthn.
- Registration and login are driven by `/auth/passkey/*` routes.
- Challenges are stored server side, single use, and expire after the configured TTL.
- The last active passkey cannot be revoked (LAST_PASSKEY error).
- Device signed JWTs are used for request authentication after login.

For configuration, deployment notes, and data model details, see `docs/auth/passkeys.md`.
