## 2024-05-18 - Centralize scope manipulation domain logic
**Learning:** Ad-hoc list comprehension and tuple unpacking for authorization scope modification (`add`, `remove`) leads to scattered, bug-prone state manipulation. Scope logic often requires deduping and order preservation, which shouldn't be re-implemented at call sites.
**Action:** Extract list manipulation of custom value objects (like `Scope`) into pure functions (`add_scopes`, `remove_scopes`) alongside the parsing logic to centralize domain rules and improve composability, avoiding repeated serialization edge cases.
