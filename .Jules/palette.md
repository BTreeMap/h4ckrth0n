## 2024-08-15 - Make hover-revealed elements keyboard accessible
**Learning:** When using Tailwind to hide interactive elements until hovered (e.g., `opacity-0 group-hover:opacity-100`), they remain invisible to keyboard users who navigate via Tab.
**Action:** Always include `focus-visible:opacity-100` (or `group-focus-within:opacity-100`) alongside `group-hover:opacity-100` to ensure the element is visible to keyboard users when focused.
