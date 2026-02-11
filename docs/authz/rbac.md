# RBAC and scopes

h4ckath0n uses server side authorization that is derived from the database.

## Roles

The built in roles are:

- `user`
- `admin`

Roles are stored on the `users.role` column and are not stored in JWTs.

## Scopes

Scopes are stored as a comma separated string in `users.scopes`. The helpers split the value on
commas and ignore empty entries.

## Dependencies

`h4ckath0n.auth.dependencies` exposes helpers for protecting routes:

- `require_user()` returns the authenticated `User`.
- `require_admin()` raises 403 unless the user role is `admin`.
- `require_scopes("scope:a", "scope:b")` raises 403 unless the user has all scopes.

## Example

```python
from fastapi import FastAPI
from h4ckath0n.auth import require_admin

app = FastAPI()

@app.get("/admin")
def admin_only(user=require_admin()):
    return {"id": user.id, "role": user.role}
```
