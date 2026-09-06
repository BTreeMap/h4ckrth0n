## 2024-08-08 - Extract Pure Scope Transformations
**Learning:** Ad-hoc list mutations and string (de)serializations (like scope manipulations in CLI commands) are hard to test effectively and lead to duplication. In h4ckath0n, the type of scopes often necessitates normalization.
**Action:** When working with sets of values, extract centralized pure functional transformations (like `add_scopes`, `remove_scopes`) that handle normalization internally to simplify call sites, rather than mutating logic locally in endpoints/commands.
