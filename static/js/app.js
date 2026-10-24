// LabVault application JavaScript.
// Progressive enhancement only; every form works without JavaScript.
// Destructive actions confirmed via data-confirm attributes (CSP-friendly).
// GSAP entrance animations respect prefers-reduced-motion.
(function () {
  "use strict";

  // ---------- Confirm destructive actions ----------
  function handleConfirm(event) {
    var element = event.target.closest("[data-confirm]");
    if (!element) return;
    var message = element.getAttribute("data-confirm") || "Are you sure you want to perform this action?";
    if (!window.confirm(message)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return false;
    }
  }

  if (document.addEventListener) {
    document.addEventListener("click", handleConfirm, true);
    document.addEventListener("submit", handleConfirm, true);
  }

  // ---------- Mobile sidebar toggle ----------
  (function initSidebar() {
    var toggle = document.getElementById("sidebar-toggle");
    var sidebar = document.getElementById("sidebar");
    var overlay = document.getElementById("mobile-overlay");
    if (!toggle || !sidebar || !overlay) return;

    function openMenu() {
      sidebar.classList.add("open");
      overlay.classList.add("open");
      toggle.setAttribute("aria-expanded", "true");
    }
    function closeMenu() {
      sidebar.classList.remove("open");
      overlay.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    }
    toggle.addEventListener("click", function () {
      if (sidebar.classList.contains("open")) closeMenu(); else openMenu();
    });
    overlay.addEventListener("click", closeMenu);
    window.addEventListener("resize", function () {
      if (window.innerWidth >= 900) closeMenu();
    });
  })();

  // ---------- GSAP entrance animations (reduced-motion aware) ----------
  (function initGSAP() {
    if (typeof gsap === "undefined") return;

    var prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      // Instantly reveal animated elements, no motion.
      document.querySelectorAll("[data-animate]").forEach(function (el) {
        el.style.opacity = "1";
        el.style.transform = "none";
      });
      return;
    }

    gsap.registerPlugin ? gsap.registerPlugin() : null;

    gsap.from("[data-animate='fade-up']", {
      duration: 0.5,
      y: 12,
      opacity: 0,
      ease: "power2.out",
      stagger: 0.06,
      delay: 0.1,
    });
  })();
})();
