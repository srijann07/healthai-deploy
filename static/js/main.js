/**
 * HealthAI - shared client-side behaviour.
 * Theme toggle (system-aware), cursor glow, live clock, count-up stats,
 * mobile sidebar, flash auto-dismiss, password visibility,
 * and submit-button loading states.
 */
(function () {
  "use strict";

  // ---------- Dark mode (system preference first, persisted) --------
  const THEME_KEY = "healthai-theme";

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    const icon = document.querySelector("#themeToggle i");
    if (icon) {
      icon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
    }
  }

  const savedTheme = localStorage.getItem(THEME_KEY);
  const systemPrefersLight =
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: light)").matches;
  const initialTheme = savedTheme || (systemPrefersLight ? "light" : "dark");
  applyTheme(initialTheme);
  if (!savedTheme) localStorage.setItem(THEME_KEY, initialTheme);

  document.addEventListener("click", function (event) {
    const toggle = event.target.closest("#themeToggle");
    if (!toggle) return;
    const current = document.documentElement.getAttribute("data-bs-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.classList.add("theme-anim");
    setTimeout(function () {
      document.documentElement.classList.remove("theme-anim");
    }, 400);
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
  });

  // ---------- Live topbar clock --------------------------------------
  const clock = document.querySelector("[data-clock]");
  if (clock) {
    function tickClock() {
      const now = new Date();
      const time =
        now.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
      const date = now.toLocaleDateString([], {
        weekday: "short",
        day: "numeric",
        month: "short",
      });
      clock.textContent = date + " · " + time;
    }
    tickClock();
    setInterval(tickClock, 1000);
  }

  // ---------- Count-up stats -------------------------------------------
  function animateCount(el) {
    const target = parseFloat(el.dataset.count);
    if (isNaN(target)) return;
    const decimals = (el.dataset.count.split(".")[1] || "").length;
    const duration = 1200;
    const start = performance.now();
    function frame(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = (target * eased).toFixed(decimals);
      if (progress < 1) requestAnimationFrame(frame);
    }
    el.textContent = "0";
    requestAnimationFrame(frame);
  }
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            animateCount(entry.target);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.4 }
    );
    document.querySelectorAll("[data-count]").forEach(function (el) {
      observer.observe(el);
    });
  } else {
    document.querySelectorAll("[data-count]").forEach(function (el) {
      el.textContent = el.dataset.count;
    });
  }

  // ---------- Mobile sidebar -----------------------------------------
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  const sidebarToggle = document.getElementById("sidebarToggle");

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove("open");
    if (backdrop) backdrop.classList.remove("show");
  }

  if (sidebarToggle && sidebar && backdrop) {
    sidebarToggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
      backdrop.classList.toggle("show");
    });
    backdrop.addEventListener("click", closeSidebar);
  }

  // ---------- Auto-dismiss flash alerts ------------------------------
  document.querySelectorAll("[data-autodismiss]").forEach(function (alert) {
    setTimeout(function () {
      if (window.bootstrap) {
        window.bootstrap.Alert.getOrCreateInstance(alert).close();
      } else {
        alert.remove();
      }
    }, 6000);
  });

  // ---------- Password visibility toggles ----------------------------
  document.querySelectorAll("[data-toggle-password]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const input = document.querySelector(btn.getAttribute("data-toggle-password"));
      if (!input) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      const icon = btn.querySelector("i");
      if (icon) icon.className = show ? "bi bi-eye-slash" : "bi bi-eye";
    });
  });

  // ---------- Loading state on form submit ---------------------------
  document.querySelectorAll("form[data-loading]").forEach(function (form) {
    form.addEventListener("submit", function () {
      const button = form.querySelector("button[type=submit]");
      if (!button) return;
      button.disabled = true;
      const label = button.querySelector(".btn-label");
      const spinner = button.querySelector(".spinner-border");
      if (label) label.classList.add("opacity-50");
      if (spinner) spinner.classList.remove("d-none");
    });
  });

  // ---------- Confirm destructive form submissions -------------------
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });
})();