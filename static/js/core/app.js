(function () {
  "use strict";
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("sidebarToggle");

  if (!sidebar || !toggle) return;

  const isMobile = () => window.matchMedia("(max-width: 768px)").matches;

  const SIDEBAR_PREFERENCE_KEY = "sidebarCollapsed";

  function saveSidebarPreference(isCollapsed) {
    try {
      localStorage.setItem(SIDEBAR_PREFERENCE_KEY, String(isCollapsed));
    } catch (_) {}
  }

  function toggleDesktopSidebar() {
    const shouldCollapse = !sidebar.classList.contains("collapsed");
    closeCollapsedSubmenus();
    sidebar.classList.toggle("collapsed", shouldCollapse);
    saveSidebarPreference(shouldCollapse);
  }

  // Sidebar toggle
  toggle.addEventListener("click", function () {
    if (isMobile()) {
      sidebar.classList.toggle("open");
    } else {
      toggleDesktopSidebar();
    }
  });

  function closeCollapsedSubmenus() {
    sidebar.querySelectorAll(".submenu-popover").forEach((item) => {
      item.classList.remove("submenu-popover");
    });
  }

  // A collapsed group icon opens a compact popover instead of widening the sidebar.
  sidebar.querySelector(".sidebar-nav")?.addEventListener("click", function (event) {
    const groupLink = event.target.closest('.nav-link[data-bs-toggle="collapse"]');
    if (!groupLink || isMobile() || !sidebar.classList.contains("collapsed")) return;

    event.preventDefault();
    event.stopPropagation();

    const groupItem = groupLink.closest("li");
    const wasOpen = groupItem?.classList.contains("submenu-popover");
    closeCollapsedSubmenus();
    if (!wasOpen && groupItem) groupItem.classList.add("submenu-popover");
  });

  document.addEventListener("click", function (event) {
    if (!sidebar.classList.contains("collapsed") || sidebar.contains(event.target)) return;
    closeCollapsedSubmenus();
  });
  // Auto-hide alerts after 2 seconds
  function autoHideAlerts() {
    const alerts = document.querySelectorAll(".alert:not(.alert-persistent)");
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
        confirmButtonColor: '#dc3545',
        confirmButtonText: '確定',
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
    },
    showLoading: (msg = '正在處理中，請稍候...') => {
      const overlay = document.getElementById('globalLoadingOverlay');
      const text = document.getElementById('globalLoadingText');
      if (overlay) {
        if (text) text.innerText = msg;
        overlay.style.display = 'flex';
      }
    },
    hideLoading: () => {
      const overlay = document.getElementById('globalLoadingOverlay');
      if (overlay) overlay.style.display = 'none';
    }
  };
  autoHideAlerts();
  window.autoHideAlerts = autoHideAlerts;

  // 主題切換
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const themeIcon = document.getElementById('themeIcon');

  if (themeToggleBtn && themeIcon) {
    if (document.documentElement.getAttribute('data-theme') === 'dark') {
      themeIcon.classList.replace('bi-sun', 'bi-moon');
    }

    themeToggleBtn.addEventListener('click', () => {
      let theme = document.documentElement.getAttribute('data-theme');
      if (theme === 'dark') {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
        themeIcon.classList.replace('bi-moon', 'bi-sun');
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        themeIcon.classList.replace('bi-sun', 'bi-moon');
      }
    });
  }

})();
