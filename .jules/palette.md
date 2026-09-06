## 2025-02-21 - Absolute Positioned Focus Rings
**Learning:** Absolute positioned interactive elements inside inputs (like password toggles) lose their native focus rings and can become invisible to keyboard users when tabbing.
**Action:** Always explicitly add focus ring styling (e.g., `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary`) to these nested interactive elements to ensure they remain accessible.
