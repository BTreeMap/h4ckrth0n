## 2024-05-15 - Keyboard Accessibility for Hover-Revealed Elements
**Learning:** Elements hidden with `opacity-0` and revealed on hover (`group-hover:opacity-100`) become inaccessible to keyboard users because they remain visually hidden when focused.
**Action:** Always pair `opacity-0 group-hover:opacity-100` with `focus-visible:opacity-100` (or `group-focus-within:opacity-100`) to ensure interactive elements are visible when receiving keyboard focus.
