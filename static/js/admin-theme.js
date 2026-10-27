"use strict";

(() => {
  const buttons = document.querySelectorAll("#branding .admin-theme-toggle");
  const theme = document.documentElement;
  const applyTheme = (mode) => {
    theme.dataset.theme = mode;
    buttons.forEach((button) => {
      button.setAttribute("aria-pressed", String(mode === "dark"));
    });
  };
  let storedTheme;
  try {
    storedTheme = localStorage.getItem("theme");
  } catch (error) {
    storedTheme = null;
  }
  if (storedTheme === "light" || storedTheme === "dark") {
    applyTheme(storedTheme);
  } else {
    applyTheme(
      window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light",
    );
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const nextTheme = theme.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
      try {
        localStorage.setItem("theme", nextTheme);
      } catch (error) {
        return;
      }
    });
  });
})();
