## 2024-10-24 - Accessibility of hover-revealed actions
**Learning:** Using `opacity-0 group-hover:opacity-100` to hide interactive elements until hovered makes them completely invisible to keyboard-only users who navigate via Tab.
**Action:** Always pair hover-revealed classes with focus states (e.g., `focus-visible:opacity-100` or `group-focus-within:opacity-100`) to ensure they become visible when receiving keyboard focus.
