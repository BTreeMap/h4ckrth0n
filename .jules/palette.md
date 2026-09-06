## 2025-01-29 - Keyboard accessibility for custom inputs and hover elements
 **Learning:** When creating accessible UI elements with `sr-only` inputs inside `<label>` wrappers, or action buttons hidden by `opacity-0 group-hover:opacity-100`, native focus states are lost or invisible to keyboard users.
 **Action:** In Tailwind v4, apply `has-[:focus-visible]:ring-2` (and related ring utilities) on the wrapper to reveal focus for screen-reader-only inputs, and add `focus-visible:opacity-100` alongside hover classes to expose hidden actions to keyboard navigation.
