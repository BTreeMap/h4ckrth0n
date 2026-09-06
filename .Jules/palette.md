## 2025-02-15 - Missing focus visibility on hover-only revealed elements
**Learning:** The "edit passkey" button in the Settings page used `opacity-0 group-hover:opacity-100` to hide it until hovered. This pattern makes it invisible during keyboard navigation.
**Action:** Always pair `opacity-0 group-hover:opacity-100` with `focus-visible:opacity-100` on interactive elements to ensure they become visible when receiving keyboard focus.
