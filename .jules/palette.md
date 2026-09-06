## 2024-07-19 - Password Toggle Keyboard Focus
**Learning:** Absolute positioned interactive elements inside inputs (such as password visibility toggles) often miss native focus rings or inherit clipped bounds.
**Action:** Always explicitly add focus ring styling (e.g., `focus-visible:outline-none focus-visible:ring-2`) to these elements to ensure they are visible during keyboard navigation.
