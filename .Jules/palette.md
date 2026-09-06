## 2024-03-20 - Focus Rings on Absolute Positioned Interactive Elements
**Learning:** Absolute positioned interactive elements inside inputs (such as password visibility toggles) often miss native focus rings or inherit clipped bounds.
**Action:** Always explicitly add focus ring styling (`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-xl`) to these elements to ensure they are visible during keyboard navigation.
