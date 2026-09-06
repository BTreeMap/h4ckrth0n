# Bolt Journal: Critical Learnings

## 2026-03-12 - Do Not Default to Materializing a Set for Scope Checks

**Learning:** In `require_scopes`, converting `user.scopes` into a `set` is not always the best optimization. For code like `needed.difference(user_scopes_iterable)`, CPython can consume a generic iterable and discard from a copied set of required scopes, so the operation can still be efficient without first building `user_scopes` as a set. Building a set eagerly adds memory overhead and may not improve the overall algorithm.

**Action:** Do not blindly convert iterables to sets just for "O(1) lookup". First check the actual operation being performed. If using set operations such as `difference` against an iterable, it may already be efficient enough. Only materialize a set when repeated membership tests or reuse clearly justify it.

## 2026-03-12 - Optimize for the Real Requirement: Full Missing Set vs One Witness

**Learning:** The best implementation depends on product requirements. If the goal is to report all missing scopes, `needed.difference(user_scopes_iterable)` is simple and efficient. If the goal is only to detect failure and report one missing scope, a manual loop over a mutable `remaining` set can use less memory and support early success once all required scopes have been seen.

**Action:** Match the data structure and algorithm to the actual API requirement. Use `difference(...)` when you need the full missing set. Use a `remaining.discard(...)` loop when you only need a witness and want tighter control over per-request allocation and early return behavior.

## 2026-03-12 - Avoid Overstated Performance Rationales in Comments

**Learning:** Comments like "convert to set for O(1) membership testing" can be misleading when the code is not actually doing repeated membership checks. In this case, the important question is the whole operation shape, not a generic rule about sets being faster.

**Action:** Write comments that describe the actual algorithm and why it was chosen in context. Prefer precise explanations over cargo-cult performance slogans.

## 2026-03-13 - Avoid ORM Hydration for ID Fetches

**Learning:** When retrieving a single field (like a primary key ID) from the database, querying for the full ORM object using `db.execute(select(Model)).scalars().first()` forces SQLAlchemy to parse, allocate, and hydrate the entire model instance, including potentially large fields like JSON blocks or long texts.
**Action:** Always use `db.scalar(select(Model.id)...)` when only the identifier is needed. This avoids the ORM overhead and significantly reduces database bandwidth and memory allocation.

## 2026-03-17 - Utilize `db.get()` for Primary Key Lookups

**Learning:** When retrieving objects by primary key, using `db.execute(select(Model).filter(Model.id == pk)).scalars().first()` bypasses the SQLAlchemy identity map and always triggers a database query, in addition to carrying the overhead of parsing and hydration. Since this is often used in high-frequency hot paths (like device JWT authentication), it becomes a measurable performance bottleneck.

**Action:** Always use `await db.get(Model, pk)` when looking up a single record by its primary key. This checks the current session's identity map first, avoiding a roundtrip to the database and bypassing parsing overhead if the object is already loaded.
