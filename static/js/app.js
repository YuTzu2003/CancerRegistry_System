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
        alert.style.transition = "opacity 0.5s ease";
        alert.style.opacity = "0";
        setTimeout(() => {
          alert.style.display = "none";
        }, 500);
      }, 2000);
    });
  }

  // Global Alert System using SweetAlert2
  window.utils = {
    toast: (msg, icon = 'success') => {
      Swal.fire({
        text: msg,
        icon: icon,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true
      });
    },
    alert: (msg, icon = 'info') => {
      return Swal.fire({
        text: msg,
        icon: icon,
        confirmButtonColor: '#0d6efd',
      });
    },
    confirm: (msg, title = '確認操作') => {
      return Swal.fire({
        title: title,
        text: msg,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: '確定',
        cancelButtonText: '取消'
      });
    },
    confirmForm: async (e, msg) => {
      e.preventDefault();
      const form = e.target;
      const confirmed = await window.utils.confirm(msg);
      if (confirmed.isConfirmed) {
        form.submit();
      }
    }
  };

  // Run on initial load
  autoHideAlerts();
  window.autoHideAlerts = autoHideAlerts;

})();
