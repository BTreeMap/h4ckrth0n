## 2024-05-24 - Missing Focus Rings on Absolute Positioned Inputs
 **Learning:** Absolute positioned interactive elements inside inputs (like password toggles) often miss native focus rings and fail keyboard accessibility.
 **Action:** Always explicitly add focus ring styling (e.g., focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary) to these inner elements.
