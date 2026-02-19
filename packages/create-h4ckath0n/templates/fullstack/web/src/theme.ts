export type ThemePreference = "system" | "light" | "dark";

export const THEME_STORAGE_KEY = "theme-preference";

export function readThemePreference(): ThemePreference {
  if (typeof window === "undefined") return "system";
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
}

export function writeThemePreference(pref: ThemePreference): void {
  localStorage.setItem(THEME_STORAGE_KEY, pref);
  window.dispatchEvent(new CustomEvent("theme-preference-change", { detail: pref }));
}

export function getEffectiveTheme(pref: ThemePreference): "light" | "dark" {
  return pref === "system"
    ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    : pref;
}

export function applyThemePreference(pref: ThemePreference): "light" | "dark" {
  writeThemePreference(pref);
  const effective = getEffectiveTheme(pref);
  document.documentElement.setAttribute("data-theme", effective);
  return effective;
}

export function subscribeToSystemThemeChanges(cb: () => void): () => void {
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  if (typeof mediaQuery.addEventListener === "function") {
    mediaQuery.addEventListener("change", cb);
  } else {
    mediaQuery.addListener(cb);
  }
  return () => {
    if (typeof mediaQuery.removeEventListener === "function") {
      mediaQuery.removeEventListener("change", cb);
    } else {
      mediaQuery.removeListener(cb);
    }
  };
}
