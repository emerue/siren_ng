/**
 * Coordinator queue auto-refresh.
 *
 * A meta-refresh would yank the page out from under someone mid-triage, so this
 * reloads only while the coordinator is idle: any typing, clicking, scrolling or
 * tab-switching cancels the pending reload until they settle again.
 */
(function () {
  "use strict";

  var script = document.currentScript ||
    document.querySelector('script[data-refresh-seconds]');
  var seconds = parseInt((script && script.dataset.refreshSeconds) || "30", 10);
  if (!seconds || seconds < 5) return;

  var label = document.querySelector("[data-refresh-label]");
  var timer = null;
  var deadline = 0;

  function tick() {
    if (!label) return;
    var left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
    label.textContent = document.hidden
      ? "Paused"
      : "Refreshing in " + left + "s";
  }

  function schedule() {
    clearTimeout(timer);
    deadline = Date.now() + seconds * 1000;
    tick();
    timer = setTimeout(function () {
      // Never reload a hidden tab or one the user is interacting with; just
      // wait for them to come back.
      if (document.hidden) { schedule(); return; }
      window.location.reload();
    }, seconds * 1000);
  }

  ["focusin", "input", "scroll", "click"].forEach(function (evt) {
    document.addEventListener(evt, schedule, { passive: true });
  });
  document.addEventListener("visibilitychange", schedule);
  setInterval(tick, 1000);
  schedule();
})();
