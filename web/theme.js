// Apply the saved palette before styles render, avoiding a flash on reload.
(() => {
  const colors = {
    forest: "#111414",
    midnight: "#141321",
    ocean: "#0b1922",
    daylight: "#f4f6fa",
  };
  const storageKey = "lingua-theme";
  const valid = (theme) => Object.hasOwn(colors, theme);

  function apply(theme) {
    const selected = valid(theme) ? theme : "forest";
    document.documentElement.dataset.theme = selected;
    document.querySelector('meta[name="theme-color"]').content = colors[selected];
    const select = document.getElementById("theme-select");
    if (select) select.value = selected;
  }

  let saved = "forest";
  try {
    saved = localStorage.getItem(storageKey) || saved;
  } catch {
    // Themes still work for this page when browser storage is restricted.
  }
  apply(saved);

  document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("theme-select");
    select.value = document.documentElement.dataset.theme;
    select.addEventListener("change", () => {
      apply(select.value);
      try {
        localStorage.setItem(storageKey, select.value);
      } catch {
        // Keep the current palette usable even without persistence.
      }
    });
  });

  // Keep multiple tabs of the same workspace in sync.
  window.addEventListener("storage", (event) => {
    if (event.key === storageKey || event.key === null) apply(event.newValue);
  });
})();
