## 2025-08-03 - Centralizing pure scope transformations
**Learning:** The logic for adding and removing scopes was duplicated and mixed with database mutation logic in the CLI. By centralizing it into `add_scopes` and `remove_scopes` within the authz domain, the semantics are explicit and simpler to test.
**Action:** Prefer extracting pure functional transformations over performing multi-step state mutations within command handlers.
