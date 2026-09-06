## 2024-05-15 - Add focus ring to absolute interactive elements inside inputs
**Learning:** Absolute positioned interactive elements inside inputs (like password visibility toggles) often miss native focus rings or inherit clipped bounds in our component structure.
**Action:** Always explicitly add focus ring styling (e.g., `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-xl`) to these elements to ensure keyboard accessibility.
