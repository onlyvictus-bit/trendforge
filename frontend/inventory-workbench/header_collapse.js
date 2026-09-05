(function () {
  "use strict";

  function toggleHeaderKPIs() {
    const header = document.getElementById("inventory-header");
    const button = document.getElementById("header-kpi-toggle");
    if (!header || !button) return false;

    const collapsed = !header.classList.contains("kpis-collapsed");
    header.classList.toggle("kpis-collapsed", collapsed);
    button.textContent = collapsed ? "⌄" : "⌃";
    button.setAttribute("aria-expanded", collapsed ? "false" : "true");
    button.setAttribute("aria-label", collapsed ? "Show inventory summary cards" : "Hide inventory summary cards");
    button.title = collapsed ? "Show inventory summary cards" : "Hide inventory summary cards";
    return collapsed;
  }

  const button = document.getElementById("header-kpi-toggle");
  if (button) button.addEventListener("click", toggleHeaderKPIs);
  window.toggleHeaderKPIs = toggleHeaderKPIs;
})();
