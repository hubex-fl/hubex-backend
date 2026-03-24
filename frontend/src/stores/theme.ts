import { defineStore } from "pinia";
import { ref } from "vue";

export type Theme = "dark" | "light";

const STORAGE_KEY = "hubex-theme";

export const useThemeStore = defineStore("theme", () => {
  const theme = ref<Theme>(
    (localStorage.getItem(STORAGE_KEY) as Theme | null) ??
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
  );

  function _apply(t: Theme) {
    document.documentElement.setAttribute("data-theme", t);
    // Keep Tailwind darkMode class in sync too
    if (t === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }

  function initFromStorage(): void {
    _apply(theme.value);
  }

  function toggleTheme(): void {
    theme.value = theme.value === "dark" ? "light" : "dark";
    localStorage.setItem(STORAGE_KEY, theme.value);
    _apply(theme.value);
  }

  function setTheme(t: Theme): void {
    theme.value = t;
    localStorage.setItem(STORAGE_KEY, t);
    _apply(t);
  }

  // Apply on creation
  _apply(theme.value);

  return { theme, initFromStorage, toggleTheme, setTheme };
});
