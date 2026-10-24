// LabVault — application JavaScript.
// No framework, no AI features. Progressive enhancement only; every form
// works without JavaScript. Confirms destructive actions triggered by data
// attributes so templates stay free of inline event handlers (CSP-friendly).
(function () {
  "use strict";

  var confirmSelectors =
    'form[data-confirm], button[data-confirm], a[data-confirm]';

  function getMessage(element) {
    return (
      element.getAttribute("data-confirm") ||
      "Are you sure you want to perform this action?"
    );
  }

  function handleConfirm(event) {
    var element = event.target.closest("[data-confirm]");
    if (!element) {
      return;
    }
    if (!window.confirm(getMessage(element))) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return false;
    }
  }

  if (document.addEventListener) {
    document.addEventListener("click", handleConfirm, true);
    document.addEventListener("submit", handleConfirm, true);
  }
})();
