(function () {
  var storageKey = "chakra-ui-color-mode";
  var root = document.documentElement;

  function getCurrentMode() {
    var mode = root.getAttribute("data-theme");
    return mode === "dark" ? "dark" : "light";
  }

  function applyMode(mode) {
    root.setAttribute("data-theme", mode);
    root.style.colorScheme = mode;
    try {
      window.localStorage.setItem(storageKey, mode);
    } catch (e) {}
    updateToggleButtons(mode);
  }

  function modeLabel(mode) {
    return mode === "dark" ? "Switch to light mode" : "Switch to dark mode";
  }

  function modeIcon(mode) {
    return mode === "dark" ? "\u2600" : "\u263D";
  }

  function updateToggleButtons(mode) {
    var buttons = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute("aria-label", modeLabel(mode));
      buttons[i].setAttribute("title", modeLabel(mode));
      buttons[i].textContent = modeIcon(mode);
    }
  }

  function toggleMode() {
    var nextMode = getCurrentMode() === "dark" ? "light" : "dark";
    applyMode(nextMode);
  }

  function bindToggles() {
    var buttons = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener("click", function (event) {
        event.preventDefault();
        toggleMode();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      updateToggleButtons(getCurrentMode());
      bindToggles();
    });
  } else {
    updateToggleButtons(getCurrentMode());
    bindToggles();
  }
})();
