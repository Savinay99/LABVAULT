/* Landing page GSAP enhancements.
   Hero entrance and scroll reveals only. Respects prefers-reduced-motion.
   Requires gsap and ScrollTrigger (loaded locally as gsap.min.js).
*/
(function () {
  "use strict";

  if (typeof gsap === "undefined") return;

  var prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReduced) {
    document.querySelectorAll("[data-animate], .hero-graphic svg").forEach(function (el) {
      el.style.opacity = "1";
      el.style.transform = "none";
    });
    return;
  }

  gsap.registerPlugin ? gsap.registerPlugin() : null;

  // Hero entrance.
  gsap.from(".hero-graphic svg", {
    duration: 0.8,
    y: 16,
    opacity: 0,
    ease: "power2.out",
    delay: 0.2,
  });
  gsap.from(".hero h1, .hero .lead, .hero-actions", {
    duration: 0.6,
    y: 12,
    opacity: 0,
    ease: "power2.out",
    stagger: 0.1,
    delay: 0.35,
  });

  // Scroll reveals (needs ScrollTrigger plugin; no-op if not loaded).
  if (typeof gsap.registerPlugin === "function" && window.ScrollTrigger) {
    gsap.registerPlugin(ScrollTrigger);
    gsap.utils.toArray("[data-animate='fade-up']").forEach(function (el) {
      gsap.from(el, {
        duration: 0.5,
        y: 12,
        opacity: 0,
        ease: "power2.out",
        scrollTrigger: {
          trigger: el,
          start: "top 85%",
          toggleActions: "play none none reverse",
        },
      });
    });
  }
})();
