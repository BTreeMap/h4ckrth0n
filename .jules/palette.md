## 2024-05-23 - Accessible hidden icon buttons
**Learning:** Using `opacity-0` with `group-hover:opacity-100` for inline action buttons (like editing a row) makes them completely invisible to keyboard users who are tabbing through. Also, icon-only buttons need `title` attributes (tooltips) for mouse users since they lack visual labels, even if they have `aria-label`.
**Action:** Always include `focus-visible:opacity-100` alongside hover-reveals, and add `title` tooltips for icon-only buttons.
