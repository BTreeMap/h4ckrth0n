## 2025-02-15 - Prefer pure helpers over inline staging logic
**Learning:** The CLI command handlers used ad-hoc inline multi-step parsing, deduplication, and set logic to combine or remove scopes. This obscured the core transformation and duplicated semantics logic inside side-effect-heavy command handlers.
**Action:** When working with collections of domain types like scopes, define centralized pure functional transformations (like `add_scopes` and `remove_scopes`) alongside the types, rather than performing multi-step state mutations inline.
