## 2024-08-09 - Scope string concatenation type mixing
 **Learning:** When creating scope manipulation helpers in `h4ckath0n.auth.authz`, combining raw iterables of strings with parsed `list[Scope]` without explicitly re-parsing all arguments causes type-mixing which eventually breaks serialization.
 **Action:** Always parse arguments (e.g. `parse_scopes(existing)` and `parse_scopes(to_add)`) before unpacking them together into a tuple for the final deduplicating `parse_scopes` call.
