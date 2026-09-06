## 2024-05-24 - Missing focus rings on absolute positioned inputs
 **Learning:** Absolute positioned interactive elements inside inputs (like password visibility toggles) in this app's components miss native focus rings and inherit clipped bounds, making them invisible during keyboard navigation.
 **Action:** Always explicitly add focus ring styling (`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary`) and appropriate border radius to these elements.
