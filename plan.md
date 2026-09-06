1. **Explore `h4ckath0n.auth.authz`**: Look at `src/h4ckath0n/auth/authz.py`. We have `parse_scopes`, `serialize_scopes`, and `missing_scopes`.
2. **Review `src/h4ckath0n/cli/users.py` and `src/h4ckath0n/auth/dependencies.py`**:
   - In `cli/users.py`, there is a lot of ad-hoc mutative logic to add, remove, and set scopes:
     ```python
     existing = parse_scopes(user.scopes)
     user.scopes = serialize_scopes((*existing, *parse_scopes(args.scope)))
     ```
     and
     ```python
     existing = parse_scopes(user.scopes)
     to_remove = set(parse_scopes(args.scope))
     remaining = [s for s in existing if s not in to_remove]
     user.scopes = serialize_scopes(remaining)
     ```
   - These could be centralized in `authz.py` as pure helper functions, `add_scopes` and `remove_scopes`.
   - Also note from memory: "Project Context / Scope Handling: When implementing or modifying scope helpers (like `add_scopes`) in `h4ckath0n.auth.authz`, always parse all inputs using `parse_scopes` before combining them... Concatenating raw strings or iterables directly with parsed `Scope` lists before serialization will cause type mixing and functional regressions."

3. **Plan**:
   - Extract `add_scopes` and `remove_scopes` into `src/h4ckath0n/auth/authz.py`. Both should accept `existing: str | Iterable[str]` and `to_add/to_remove: str | Iterable[str]`. Both should parse the inputs, perform the pure functional transformation, and return a `list[Scope]`. Actually, better if they return the string representation directly (or not, `parse_scopes` returns `list[Scope]`. The CLI does `user.scopes = serialize_scopes(add_scopes(user.scopes, args.scope))`). Let's make them return `list[Scope]` for composability or `str`. I will make them return `list[Scope]`. Wait, maybe even better if `add_scopes` and `remove_scopes` just do the list transformation, and CLI still does serialization, or wait, it's better if the helpers return `list[Scope]` so they can be serialized easily.
   - Wait, `authz.py` is about domain types. `add_scopes(existing, to_add) -> list[Scope]` and `remove_scopes(existing, to_remove) -> list[Scope]`. Let's implement these two helpers.
