/* html_review print.js -- handles the Export PDF button.
   Adds body.exporting, triggers browser print dialog, cleans up. */

(function () {
  "use strict";

  const btn = document.getElementById("btn-export");
  if (!btn) return;

  btn.addEventListener("click", () => {
    const selected = document.querySelectorAll(".analysis-wrapper.selected");
    if (selected.length === 0) {
      alert("Select at least one analysis to export.");
      return;
    }

    /* Mark empty sections so the print CSS can hide them */
    document.querySelectorAll(".review-section").forEach((s) => {
      const hasSelected = s.querySelector(".analysis-wrapper.selected");
      s.classList.toggle("empty", !hasSelected);
    });

    document.body.classList.add("exporting");

    /* Open the browser print dialog after the CSS has applied */
    setTimeout(() => window.print(), 100);
  });

  window.addEventListener("afterprint", () => {
    document.body.classList.remove("exporting");
    document.querySelectorAll(".review-section.empty").forEach((s) => {
      s.classList.remove("empty");
    });
  });
})();
