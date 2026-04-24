/* html_review app.js -- selection tray, scroll-spy, keyboard, sheet switcher.
   Vanilla JS. No dependencies. */

(function () {
  "use strict";

  const clientId = document.body.dataset.client || "unknown";
  const month = document.body.dataset.month || "unknown";
  const storageKey = `hr-selection-${clientId}-${month}`;

  const countEl = document.getElementById("selection-count");
  const btnClear = document.getElementById("btn-clear");
  const boxes = document.querySelectorAll(".select-box");

  function loadSelection() {
    try {
      return new Set(JSON.parse(localStorage.getItem(storageKey) || "[]"));
    } catch {
      return new Set();
    }
  }

  function saveSelection(set) {
    localStorage.setItem(storageKey, JSON.stringify([...set]));
  }

  const selected = loadSelection();

  function applySelectionToDOM() {
    boxes.forEach((box) => {
      const id = box.dataset.blockId;
      const wrapper = box.closest(".analysis-wrapper");
      if (selected.has(id)) {
        box.checked = true;
        wrapper.classList.add("selected");
      } else {
        box.checked = false;
        wrapper.classList.remove("selected");
      }
    });
    countEl.textContent = String(selected.size);
  }

  boxes.forEach((box) => {
    box.addEventListener("change", () => {
      const id = box.dataset.blockId;
      if (box.checked) selected.add(id);
      else selected.delete(id);
      saveSelection(selected);
      applySelectionToDOM();
    });
  });

  btnClear.addEventListener("click", () => {
    selected.clear();
    saveSelection(selected);
    applySelectionToDOM();
  });

  /* Keyboard: 'S' toggles the nearest block to viewport center */
  document.addEventListener("keydown", (e) => {
    if (e.key !== "s" && e.key !== "S") return;
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
    const wrappers = [...document.querySelectorAll(".analysis-wrapper")];
    const center = window.scrollY + window.innerHeight / 2;
    let best = null;
    let bestDist = Infinity;
    wrappers.forEach((w) => {
      const r = w.getBoundingClientRect();
      const mid = r.top + window.scrollY + r.height / 2;
      const dist = Math.abs(mid - center);
      if (dist < bestDist) {
        bestDist = dist;
        best = w;
      }
    });
    if (best) {
      const box = best.querySelector(".select-box");
      box.checked = !box.checked;
      box.dispatchEvent(new Event("change"));
    }
  });

  /* Scroll-spy: highlights sidebar link of the section currently on screen */
  const sectionEls = document.querySelectorAll(".review-section");
  const linkEls = document.querySelectorAll(".sidebar-section");
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.dataset.section;
          linkEls.forEach((link) => {
            link.classList.toggle(
              "active",
              link.dataset.sectionTarget === id
            );
          });
        }
      });
    },
    { rootMargin: "-40% 0px -55% 0px" }
  );
  sectionEls.forEach((el) => observer.observe(el));

  /* Multi-sheet select switcher inside data tables */
  document.querySelectorAll(".sheet-select").forEach((sel) => {
    sel.addEventListener("change", () => {
      const details = sel.closest(".data-table");
      const idx = parseInt(sel.value, 10);
      details.querySelectorAll(".sheet").forEach((t) => {
        t.hidden = parseInt(t.dataset.sheetIdx, 10) !== idx;
      });
    });
  });

  applySelectionToDOM();
})();
