## 2024-05-24 - Focus rings on absolute positioned interactive elements
 **Learning:** Absolute positioned interactive elements inside inputs (such as password visibility toggles) often miss native focus rings or inherit clipped bounds, rendering them invisible during keyboard navigation.
 **Action:** Always explicitly add focus ring styling (e.g., `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary`) and appropriate border radius to these elements.
