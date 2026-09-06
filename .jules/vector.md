## 2024-08-01 - Centralize scope manipulations into pure functions
 **Learning:** Scope manipulation (adding/removing) was scattered across the CLI code, leading to repeated parsing logic and potential ordering/deduplication bugs if concatenated wrongly.
 **Action:** Extract scope mutations into composable, pure domain helpers (`add_scopes`, `remove_scopes`) that parse inputs before combining them. This keeps the domain semantics centralized in `authz.py` and leaves call sites as a clear transformation pipeline.
