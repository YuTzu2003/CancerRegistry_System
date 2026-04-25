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

  // Close mobile sidebar when clicking outside
  document.addEventListener("click", function (e) {
    if (!isMobile()) return;
    if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
      sidebar.classList.remove("open");
    }
  });

})();
