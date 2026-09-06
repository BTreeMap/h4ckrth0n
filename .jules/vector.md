## 2024-07-30 - Centralise authorization scope manipulation
**Learning:** CLI utilities manually deserialized, manipulated, and reserialized user scopes, duplicating string normalization logic and separating it from the core domain parsing functions in `h4ckath0n.auth.authz`.
**Action:** Ensure scope string manipulations are abstracted as pure helper pipelines (`add_scopes`, `remove_scopes`) inside the `h4ckath0n.auth.authz` module, parsing all variadic or raw string inputs to apply unified deduplication and order-preservation before serialization.
