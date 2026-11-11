/**
 * LabVault GSAP Orchestration
 * Subdued, purposeful micro-animations.
 * Durations 0.2s - 0.4s, subtle translate offsets (4px - 10px).
 * Gracefully defaults to static display if JS or GSAP fails or prefers-reduced-motion is active.
 */
(function () {
  "use strict";

  if (typeof gsap === "undefined") {
    return;
  }

  var prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReduced) {
    return;
  }

  // Animate page header
  var pageHeader = document.querySelector(".page-header");
  if (pageHeader) {
    gsap.from(pageHeader, {
      opacity: 0,
      y: -6,
      duration: 0.3,
      ease: "power2.out"
    });
  }

  // Animate stats cards with short staggered entrance
  var statCards = document.querySelectorAll(".stat-card");
  if (statCards.length > 0) {
    gsap.from(statCards, {
      opacity: 0,
      y: 8,
      duration: 0.35,
      stagger: 0.05,
      ease: "power2.out"
    });
  }

  // Animate resource cards with enhanced smooth stagger
  var resourceCards = document.querySelectorAll(".resource-card");
  if (resourceCards.length > 0) {
    gsap.from(resourceCards, {
      opacity: 0,
      y: 16,
      duration: 0.45,
      stagger: 0.06,
      ease: "power2.out"
    });
  }

  // Animate auth card entrance
  var authCard = document.querySelector(".auth-card");
  if (authCard) {
    gsap.from(authCard, {
      opacity: 0,
      y: 14,
      scale: 0.98,
      duration: 0.45,
      ease: "power2.out"
    });
  }

  // Animate Hero Section & Stepped Ribbons (Labrina style micro-animations)
  var heroBadge = document.querySelector(".hero-badge-pill");
  if (heroBadge) {
    gsap.from(heroBadge, {
      opacity: 0,
      y: -8,
      duration: 0.4,
      ease: "power2.out"
    });
  }

  var heroTitle = document.querySelector(".hero-title-editorial");
  if (heroTitle) {
    gsap.from(heroTitle, {
      opacity: 0,
      y: 14,
      duration: 0.55,
      delay: 0.1,
      ease: "power2.out"
    });
  }

  var heroSubtitle = document.querySelector(".hero-subtitle-clean");
  if (heroSubtitle) {
    gsap.from(heroSubtitle, {
      opacity: 0,
      y: 10,
      duration: 0.5,
      delay: 0.18,
      ease: "power2.out"
    });
  }

  var heroButtons = document.querySelectorAll(".hero-cta-group .btn-pill");
  if (heroButtons.length > 0) {
    gsap.from(heroButtons, {
      opacity: 0,
      y: 10,
      duration: 0.4,
      stagger: 0.08,
      delay: 0.25,
      ease: "power2.out"
    });
  }

  // Animate left & right ribbon bars
  var leftBars = document.querySelectorAll(".hero-ribbon-left .ribbon-bar");
  if (leftBars.length > 0) {
    gsap.from(leftBars, {
      opacity: 0,
      x: -24,
      duration: 0.6,
      stagger: 0.05,
      ease: "power2.out"
    });
  }

  var rightBars = document.querySelectorAll(".hero-ribbon-right .ribbon-bar");
  if (rightBars.length > 0) {
    gsap.from(rightBars, {
      opacity: 0,
      x: 24,
      duration: 0.6,
      stagger: 0.05,
      ease: "power2.out"
    });
  }

  // Animate Canto wireframe dashboard preview
  var wireframeCard = document.querySelector(".wireframe-dashboard");
  if (wireframeCard) {
    gsap.from(wireframeCard, {
      opacity: 0,
      y: 22,
      scale: 0.99,
      duration: 0.65,
      delay: 0.28,
      ease: "power2.out"
    });
  }

  // Animate department ticker items
  var deptPills = document.querySelectorAll(".dept-pill");
  if (deptPills.length > 0) {
    gsap.from(deptPills, {
      opacity: 0,
      y: 8,
      duration: 0.35,
      stagger: 0.04,
      delay: 0.45,
      ease: "power2.out"
    });
  }

  // Animate flash messages
  var flashItems = document.querySelectorAll(".flash");
  if (flashItems.length > 0) {
    gsap.from(flashItems, {
      opacity: 0,
      y: -8,
      duration: 0.25,
      stagger: 0.05,
      ease: "power2.out"
    });
  }
})();
