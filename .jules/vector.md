## 2024-08-07 - Functional-style centralization of scope transformations
**Learning:** In the authorization domain, user scopes are parsed and modified in command handlers inline, utilizing state mutation via multiple variables.
**Action:** Moved the transformation logic (`add_scopes`, `remove_scopes`) into the `authz.py` module as centralized, deterministic, pure-functional helpers. This removes duplication and makes the API more composable.
