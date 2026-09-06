## 2024-03-22 - Centralize Scopes Transformations
**Learning:** The codebase has functional primitives like `parse_scopes`, `serialize_scopes`, and `missing_scopes` for scopes processing. However, mutating scope transformations are still manually written in multiple places, such as CLI add/remove commands, rather than relying on pure functional transformation helpers.
**Action:** Centralize data mutation by adding composable, pure functional helpers `add_scopes(existing, new)` and `remove_scopes(existing, to_remove)` to `authz.py`.
