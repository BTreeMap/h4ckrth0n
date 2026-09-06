## 2024-03-22 - Centralize authz scope transformations
**Learning:** Logic for adding and removing comma-separated scopes was duplicated in the CLI using ad-hoc `parse_scopes` / `serialize_scopes` manipulation, which obscures intent and misses a shared normalization boundary.
**Action:** Always centralize string serialization/manipulation (like user scopes) into pure, tested domain helpers (e.g. `add_scopes`, `remove_scopes`) rather than inline `serialize_scopes((*existing, *parse_scopes(to_add)))` at call sites.
