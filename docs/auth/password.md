# Password auth (optional)

Password routes are optional and only mount when:

1. The password extra is installed: `pip install "h4ckath0n[password]"`.
2. `H4CKATH0N_PASSWORD_AUTH_ENABLED=true` is set.

## Routes

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/password-reset/request`
- `POST /auth/password-reset/confirm`

## Behavior

- Password routes authenticate email and password, then bind a device key if provided.
- The response returns `user_id`, `device_id`, and `role`.
- No access tokens, refresh tokens, or cookies are returned.

## Password reset

- `password-reset/request` always returns the same message, even for unknown emails.
- `password-reset/confirm` validates the token and sets a new password.
- Tokens expire after `H4CKATH0N_PASSWORD_RESET_EXPIRE_MINUTES` (default 30).

## Admin bootstrapping

Password signups can set the initial role:

- `H4CKATH0N_BOOTSTRAP_ADMIN_EMAILS` accepts a JSON list of emails that should receive the admin
  role on signup.
- `H4CKATH0N_FIRST_USER_IS_ADMIN=true` grants the first password signup the admin role.

Passkey signups do not use these settings because they do not collect email addresses.
