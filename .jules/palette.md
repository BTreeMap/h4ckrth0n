## 2024-07-18 - [Accessibility] Added focus styles to absolute positioned inputs
**Learning:** Absolute positioned interactive elements inside inputs (such as password visibility toggles) often miss native focus rings or inherit clipped bounds.
**Action:** Always explicitly add focus ring styling (e.g., `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary`) to these elements to ensure they are visible during keyboard navigation.
