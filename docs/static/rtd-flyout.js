/*
 * Remove the "On Read the Docs" section (Project Home / Builds) from the
 * Read the Docs flyout menu.
 *
 * Read the Docs Addons offers no setting for this: the flyout is a
 * <readthedocs-flyout> web component and, while its shadow root is open, it
 * exposes no CSS ::part() hooks, so a stylesheet cannot reach inside. Script is
 * the only way in.
 *
 * The flyout is injected asynchronously, and re-rendered when its data
 * arrives, so this waits for the element and then keeps watching its shadow
 * root rather than pruning once.
 *
 * Unsupported by Read the Docs: it matches on the section's visible label, so
 * a future change to the flyout markup or wording will silently stop it
 * working. It fails safe - the section reappears, nothing breaks.
 */
(function () {
  "use strict";

  var SECTION = "On Read the Docs";

  function prune(root) {
    Array.prototype.forEach.call(root.querySelectorAll("dl"), function (dl) {
      var dt = dl.querySelector("dt");
      if (dt && dt.textContent.trim() === SECTION) {
        dl.remove();
      }
    });
  }

  function attach(el) {
    if (!el || !el.shadowRoot) {
      return false;
    }
    prune(el.shadowRoot);
    new MutationObserver(function () {
      prune(el.shadowRoot);
    }).observe(el.shadowRoot, { childList: true, subtree: true });
    return true;
  }

  if (attach(document.querySelector("readthedocs-flyout"))) {
    return;
  }

  var observer = new MutationObserver(function () {
    if (attach(document.querySelector("readthedocs-flyout"))) {
      observer.disconnect();
    }
  });
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
