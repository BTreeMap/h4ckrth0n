## 2024-XX-XX - Functional transformation helpers for scopes

**Learning:** When modifying user scopes, favor centralized pure functional transformations like `add_scopes` and `remove_scopes` rather than inline multi-step state mutations (like manual parsing, set comprehensions, and reserializing) within command handlers.

**Action:** Extracted `add_scopes` and `remove_scopes` into `src/h4ckath0n/auth/authz.py` to prevent scattered duplication in the CLI.
