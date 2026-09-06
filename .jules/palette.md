## 2024-10-24 - Missing focus states on absolute-positioned form icons
 **Learning:** Absolute-positioned icon-only buttons inside form fields (like password toggles) frequently lose browser default focus outlines due to Tailwind's preflight and lack explicit tooltip titles, breaking keyboard navigation visibility.
 **Action:** Always explicitly apply `focus-visible:ring-2`, `focus-visible:outline-none`, and a `title` attribute matching the ARIA label to custom interactive elements overlaid on inputs.
