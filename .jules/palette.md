## 2024-05-24 - Accessibility focus rings on absolute positioned elements
 **Learning:** Absolute positioned interactive elements inside inputs (like password visibility toggles) in this design system miss native focus rings during keyboard navigation.
 **Action:** Always explicitly add focus ring styling (`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-md`) to these elements to ensure they remain accessible to keyboard users.
