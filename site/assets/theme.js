// Runs synchronously in <head>, before first paint. Light is the default;
// a visitor who picked dark with the header toggle gets it back without a
// flash of the light theme. External file because the CSP forbids inline
// scripts. Storage can throw (private mode, blocked site data) — then the
// page simply stays light.
(function () {
  try {
    if (localStorage.getItem("fojin-ai-theme") === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    }
  } catch (e) {}
})();
