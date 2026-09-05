(function () {
  "use strict";

  function toggleSidebar() {
    const app = document.getElementById("app-container");
    const button = document.getElementById("sidebar-toggle");
    if (!app || !button) return false;

    const collapsed = !app.classList.contains("sidebar-collapsed");
    app.classList.toggle("sidebar-collapsed", collapsed);
    button.textContent = collapsed ? "›" : "‹";
    button.setAttribute("aria-expanded", collapsed ? "false" : "true");
    button.setAttribute("aria-label", collapsed ? "Show topic and field filters" : "Hide topic and field filters");
    button.title = collapsed ? "Show topic and field filters" : "Hide topic and field filters";
    return collapsed;
  }

  const button = document.getElementById("sidebar-toggle");
  if (button) button.addEventListener("click", toggleSidebar);
  window.toggleSidebar = toggleSidebar;
})();
