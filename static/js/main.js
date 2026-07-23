/* SPP Control — shared front-end behavior (sidebar, theme, confirmations, loading states). */
(function () {
  "use strict";

  /* ---------- Mobile sidebar ---------- */
  var sidebar = document.querySelector(".sidebar");
  var backdrop = document.querySelector(".sidebar-backdrop");
  var sidebarToggle = document.querySelector("[data-sidebar-toggle]");

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove("is-open");
    if (backdrop) backdrop.classList.remove("is-open");
  }

  if (sidebarToggle && sidebar && backdrop) {
    sidebarToggle.addEventListener("click", function () {
      sidebar.classList.toggle("is-open");
      backdrop.classList.toggle("is-open");
    });
    backdrop.addEventListener("click", closeSidebar);
  }

  /* ---------- Theme (light / dark) ---------- */
  var root = document.documentElement;
  var themeToggle = document.querySelector("[data-theme-toggle]");
  var THEME_KEY = "spp-theme";

  function applyTheme(theme) {
    root.setAttribute("data-bs-theme", theme);
    if (themeToggle) {
      var icon = themeToggle.querySelector("i");
      if (icon) icon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
    }
  }

  var storedTheme = localStorage.getItem(THEME_KEY);
  var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(storedTheme || (prefersDark ? "dark" : "light"));

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var isDark = root.getAttribute("data-bs-theme") === "dark";
      var next = isDark ? "light" : "dark";
      applyTheme(next);
      localStorage.setItem(THEME_KEY, next);
    });
  }

  /* ---------- Button loading state ---------- */
  function setButtonLoading(btn) {
    if (!btn) return;
    btn.classList.add("is-loading");
    btn.disabled = true;
  }

  /* ---------- Confirmation modal for destructive actions ---------- */
  var confirmModalEl = document.getElementById("confirmModal");
  var confirmModal = confirmModalEl && window.bootstrap ? new bootstrap.Modal(confirmModalEl) : null;
  var confirmModalBody = confirmModalEl ? confirmModalEl.querySelector("[data-confirm-body]") : null;
  var confirmModalBtn = confirmModalEl ? confirmModalEl.querySelector("[data-confirm-accept]") : null;
  var pendingForm = null;

  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (form.dataset.confirmed === "true") return;
      e.preventDefault();

      if (!confirmModal) {
        if (window.confirm(form.dataset.confirm)) {
          form.dataset.confirmed = "true";
          form.submit();
        }
        return;
      }

      pendingForm = form;
      if (confirmModalBody) confirmModalBody.textContent = form.dataset.confirm;
      confirmModal.show();
    });
  });

  if (confirmModalBtn) {
    confirmModalBtn.addEventListener("click", function () {
      if (!pendingForm) return;
      pendingForm.dataset.confirmed = "true";
      setButtonLoading(confirmModalBtn);
      confirmModal.hide();
      pendingForm.submit();
    });
  }

  /* Regular (non-destructive) POST forms get a loading state on their submit button */
  document.querySelectorAll("form:not([data-confirm])").forEach(function (form) {
    if ((form.method || "get").toLowerCase() === "get") return;
    form.addEventListener("submit", function () {
      setButtonLoading(form.querySelector('button[type="submit"]'));
    });
  });

  /* ---------- Auto-dismiss flash alerts ---------- */
  document.querySelectorAll(".alert-stack .alert").forEach(function (alertEl) {
    setTimeout(function () {
      if (window.bootstrap) {
        bootstrap.Alert.getOrCreateInstance(alertEl).close();
      } else {
        alertEl.remove();
      }
    }, 6000);
  });
})();
