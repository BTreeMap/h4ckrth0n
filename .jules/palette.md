## 2024-07-14 - Keyboard accessibility for custom radio buttons and hidden elements
**Learning:** Custom UI elements like hidden interactive icons (`opacity-0` revealed on hover) and visually replaced radio buttons (where native `<input>` is `sr-only`) often silently fail keyboard accessibility by lacking focus states.
**Action:** Always ensure `focus-visible:opacity-100` is applied alongside `hover:opacity-100`, and use `has-[:focus-visible]` on the wrapper label for custom radio button groups to properly highlight the active selection.
