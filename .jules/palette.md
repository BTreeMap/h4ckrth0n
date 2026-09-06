## 2024-08-01 - Missing Focus Rings on Absolute Positioned Inputs
 **Learning:** Interactive elements positioned absolutely inside inputs (like the password visibility toggle) often inherit clipped bounds or miss native focus rings, making keyboard navigation confusing because focus state becomes invisible.
 **Action:** Always explicitly add focus ring styling (e.g., `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary`) and appropriate border radii to such nested interactive elements.
