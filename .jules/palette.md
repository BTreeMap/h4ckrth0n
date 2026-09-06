## 2025-02-27 - Focus Rings on Absolute Interactive Elements
 **Learning:** Absolute positioned interactive elements inside inputs (such as password visibility toggles) often miss native focus rings or inherit clipped bounds, rendering them invisible during keyboard navigation.
 **Action:** Always explicitly add focus ring styling (e.g., `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary`) and appropriate border radius to these elements so keyboard users can track their focus state.
