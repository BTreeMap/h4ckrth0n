## 2024-08-12 - Centralized functional transformation helpers for user scopes
**Learning:** When dealing with parsed domains, prefer having functional `add_x` and `remove_x` transformation helpers centralized in the domain object representation rather than repeatedly relying on users to unpack, mutate via sets, and pack back to a string in their application boundaries.
**Action:** Added `add_scopes` and `remove_scopes` pure functions to `h4ckath0n.auth.authz`.
