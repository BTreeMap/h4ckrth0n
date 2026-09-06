## 2024-05-18 - Centralize scope manipulations
**Learning:** Scope strings were previously manually deserialized and manipulated locally across CLI functions leading to duplication.
**Action:** Replaced local mutation logic with pure composable helpers (`normalize_scopes`, `add_scopes`, `remove_scopes`) grouped near the types they operate on.
