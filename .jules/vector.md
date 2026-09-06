## 2025-01-20 - Centralize scope transformations in authz
**Learning:** Repetitive scope processing (parsing, mutating, serializing) spread across CLI routines risked diverging normalizations and was mutation-heavy.
**Action:** Created explicit `add_scopes`, `remove_scopes`, and `normalize_scopes` pure helpers in `authz.py` that handle the data-in/data-out canonicalization pipelines, replacing imperative CLI logic.
