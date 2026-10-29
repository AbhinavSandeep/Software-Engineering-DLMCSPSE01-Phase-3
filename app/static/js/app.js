// XPtoIRL: small progressive enhancements. Every page also works without JavaScript.
(function () {
  "use strict";

  // Skill selection on the start page: 1 to 3 skills (FR2).
  const form = document.getElementById("skill-form");
  if (form) {
    const MAX = 3;
    const boxes = Array.from(form.querySelectorAll(".skill-check"));
    const button = document.getElementById("find-games");
    const hint = document.getElementById("selection-hint");

    const update = () => {
      const count = boxes.filter((b) => b.checked).length;
      button.disabled = count === 0;
      boxes.forEach((b) => { b.disabled = !b.checked && count >= MAX; });
      hint.textContent = count === 0
        ? "Select 1 to 3 skills."
        : count >= MAX
          ? "Maximum of 3 skills selected."
          : `${count} selected. You can add ${MAX - count} more.`;
    };
    boxes.forEach((b) => b.addEventListener("change", update));
    update();
  }

  // Filters apply as soon as a value changes.
  const filters = document.getElementById("filter-form");
  if (filters) {
    filters.querySelectorAll("select").forEach((s) => s.addEventListener("change", () => filters.submit()));
  }
})();
