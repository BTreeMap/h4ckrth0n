## 2025-02-17 - Keyboard Accessibility for Hover-Revealed Elements
**Learning:** Using `opacity-0 group-hover:opacity-100` to hide secondary actions (like edit buttons) until hovered makes them completely invisible to keyboard-only users navigating via Tab.
**Action:** Always pair `group-hover:opacity-100` with `focus-visible:opacity-100` (or `group-focus-within:opacity-100`) so the interactive element becomes visible when it receives keyboard focus.
