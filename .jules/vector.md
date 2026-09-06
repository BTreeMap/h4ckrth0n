## 2024-08-13 - Scope Transformation Refactoring
**Learning:** When modifying data structures like user scopes, prefer calling centralized pure functional transformations (e.g., `add_scopes` and `remove_scopes` from `h4ckath0n.auth.authz`) rather than performing inline multi-step state mutations within command handlers or domain logic.
**Action:** In the future, centralize domain model transformations into pure functional helpers before applying side effects like serialization or database commits.
