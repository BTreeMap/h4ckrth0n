## 2026-08-16 - Keyboard visibility for hover-only actions
**Learning:** When using Tailwind to hide interactive elements until hovered (e.g., `opacity-0 group-hover:opacity-100`), keyboard users cannot see the element when they focus it via Tab.
**Action:** Always include `focus-visible:opacity-100` (or `group-focus-within:opacity-100`) when using `opacity-0 group-hover:opacity-100` to ensure the element becomes visible when receiving keyboard focus.
