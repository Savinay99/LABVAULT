/**
 * LabVault Application JavaScript
 * Progressive enhancement: all core functionality works without JS.
 * WCAG AA accessible, handles keyboard focus, password toggles, and mobile menu.
 */
(function () {
  "use strict";

  // Mark document as JS-enabled
  document.documentElement.classList.add("js");

  // ---------- Mobile Navigation Toggle ----------
  var mobileToggle = document.getElementById("mobile-nav-toggle");
  var siteHeader = document.getElementById("site-header");

  if (mobileToggle && siteHeader) {
    mobileToggle.addEventListener("click", function () {
      var isExpanded = mobileToggle.getAttribute("aria-expanded") === "true";
      mobileToggle.setAttribute("aria-expanded", String(!isExpanded));
      siteHeader.classList.toggle("mobile-nav-open", !isExpanded);
    });

    // Close on Escape key
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && siteHeader.classList.contains("mobile-nav-open")) {
        mobileToggle.setAttribute("aria-expanded", "false");
        siteHeader.classList.remove("mobile-nav-open");
        mobileToggle.focus();
      }
    });
  }

  // ---------- Password Visibility Toggle ----------
  document.querySelectorAll(".password-toggle-btn").forEach(function (button) {
    button.addEventListener("click", function () {
      var targetId = button.getAttribute("data-target");
      var input = targetId ? document.getElementById(targetId) : button.previousElementSibling;
      if (!input) return;

      var isPassword = input.getAttribute("type") === "password";
      input.setAttribute("type", isPassword ? "text" : "password");
      button.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");

      var icon = button.querySelector("svg");
      if (icon) {
        if (isPassword) {
          icon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>';
        } else {
          icon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>';
        }
      }
    });
  });

  // ---------- Drag and Drop File Upload Area ----------
  var dropzone = document.querySelector(".file-dropzone");
  if (dropzone) {
    var fileInput = dropzone.querySelector("input[type='file']");
    var titleEl = dropzone.querySelector(".file-dropzone-title");

    ["dragenter", "dragover"].forEach(function (eventName) {
      dropzone.addEventListener(eventName, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach(function (eventName) {
      dropzone.addEventListener(eventName, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("drag-over");
      });
    });

    if (fileInput) {
      dropzone.addEventListener("keydown", function (e) {
        if ((e.key === "Enter" || e.key === " ") && e.target === dropzone) {
          e.preventDefault();
          fileInput.click();
        }
      });

      fileInput.addEventListener("change", function () {
        if (fileInput.files && fileInput.files.length > 0 && titleEl) {
          titleEl.textContent = "Selected: " + fileInput.files[0].name;
        }
      });
    }
  }

  // ---------- Destructive Action Confirmation ----------
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      var message = el.getAttribute("data-confirm") || "Are you sure you want to proceed with this action?";
      if (!window.confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // ---------- Form Submission Loading States ----------
  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function () {
      var submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn && !submitBtn.disabled) {
        submitBtn.setAttribute("data-original-text", submitBtn.innerHTML);
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner" style="display:inline-block;width:14px;height:14px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;animation:spin 0.6s linear infinite;margin-right:8px;"></span> Processing…';
      }
    });
  });

})();
