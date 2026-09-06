## 2024-08-23 - Add focus-visible to group-hover elements
**Learning:** Found a button that only shows on hover (`opacity-0 group-hover:opacity-100`). This is completely inaccessible to keyboard users unless they also receive focus-visible styles.
**Action:** Always include `focus-visible:opacity-100` (or `group-focus-within:opacity-100`) alongside `opacity-0 group-hover:opacity-100`.
