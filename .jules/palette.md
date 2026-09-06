## 2024-08-19 - Focus visibility for group-hover interactions
**Learning:** When using Tailwind to hide interactive elements until hovered (e.g., `opacity-0 group-hover:opacity-100`), keyboard users cannot see the element when navigating with Tab if it lacks focus states.
**Action:** Always include `focus-visible:opacity-100` (or `group-focus-within:opacity-100`) alongside `group-hover:opacity-100` to ensure keyboard accessibility.
