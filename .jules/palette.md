## 2024-07-16 - Password Toggle Keyboard Accessibility
**Learning:** Absolute positioned interactive elements inside inputs (like password visibility toggles) often miss native focus rings or inherit clipped bounds, making them invisible during keyboard navigation.
**Action:** Always explicitly add `focus-visible:outline-none focus-visible:ring-2` to absolutely positioned icon buttons inside forms.
