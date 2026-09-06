## 2024-05-18 - Adding character counts to limited inputs
**Learning:** Users often lack context on form input length restrictions until they hit arbitrary limits or trigger validation errors. Adding a subtle, accessible inline character counter directly driven by the `maxLength` attribute leverages existing validation constraints for immediate UX feedback.
**Action:** Whenever introducing a `maxLength` property to a text input component, automatically expose a visual counter (and `aria-live="polite"` region) so screen reader and sighted users get real-time feedback on length limits.
