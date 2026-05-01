(function () {
  "use strict";

  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("sidebarToggle");

  if (!sidebar || !toggle) return;

  const isMobile = () => window.matchMedia("(max-width: 768px)").matches;

  // Sidebar toggle
  toggle.addEventListener("click", function () {
    if (isMobile()) {
      sidebar.classList.toggle("open");
    } else {
      sidebar.classList.toggle("collapsed");
    }
  });

  // Auto-hide alerts after 2 seconds
  function autoHideAlerts() {
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
      setTimeout(() => {
        // Use Bootstrap fade-out if possible, or simple hide
        alert.style.transition = "opacity 0.5s ease";
        alert.style.opacity = "0";
        setTimeout(() => {
          alert.style.display = "none";
        }, 500);
      }, 2000);
    });
  }

  // Run on initial load
  autoHideAlerts();

  // Export to window so other scripts can trigger it
  window.autoHideAlerts = autoHideAlerts;

})();
