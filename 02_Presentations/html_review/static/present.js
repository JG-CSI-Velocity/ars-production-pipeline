/* html_review present.js -- clicker-friendly presenter mode.
   Toggle with 'P'. Navigate with arrow keys / Space / PageUp/Down / Home / End.
   Press 'D' on an exhibit slide to reveal its data table.
   Press 'Esc' to exit detail view, or exit presenter mode.
   Vanilla JS. No dependencies. */

(function () {
  "use strict";

  const CURRENT_CLASS = "is-current-slide";
  const PRESENTING_CLASS = "presenting";
  const DETAIL_OPEN_CLASS = "detail-open";

  let slides = [];
  let currentIdx = 0;
  let presenting = false;

  const counterEl = document.getElementById("presenter-counter");
  const progressBarEl = document.getElementById("presenter-progress-bar");
  const btnPresent = document.getElementById("btn-present");

  function enumerateSlides() {
    const list = [];
    const cover = document.querySelector(".cover-page");
    if (cover) list.push(cover);
    document.querySelectorAll(".review-section").forEach((section) => {
      const header = section.querySelector(".section-header");
      if (header) list.push(header);
      section.querySelectorAll(".analysis-wrapper").forEach((a) => list.push(a));
    });
    return list;
  }

  function isExhibitSlide(el) {
    return el && el.classList && el.classList.contains("analysis-wrapper");
  }

  function hasDataTable(wrapper) {
    return !!wrapper.querySelector("details.data-table");
  }

  function updateCounter() {
    if (!counterEl) return;
    counterEl.textContent = `${currentIdx + 1} / ${slides.length}`;
  }

  function updateProgress() {
    if (!progressBarEl) return;
    const pct = slides.length > 0 ? ((currentIdx + 1) / slides.length) * 100 : 0;
    progressBarEl.style.width = `${pct}%`;
  }

  function closeDetailOn(slide) {
    if (!slide) return;
    slide.classList.remove(DETAIL_OPEN_CLASS);
    const details = slide.querySelector("details.data-table");
    if (details) details.removeAttribute("open");
  }

  function showSlide(idx) {
    if (idx < 0) idx = 0;
    if (idx >= slides.length) idx = slides.length - 1;
    const prev = slides[currentIdx];
    if (prev && prev !== slides[idx]) closeDetailOn(prev);
    currentIdx = idx;
    slides.forEach((s, i) => {
      s.classList.toggle(CURRENT_CLASS, i === idx);
    });
    updateCounter();
    updateProgress();
  }

  function enterPresenter() {
    if (presenting) return;
    slides = enumerateSlides();
    if (slides.length === 0) return;
    presenting = true;
    document.body.classList.add(PRESENTING_CLASS);
    currentIdx = 0;
    showSlide(0);
  }

  function exitPresenter() {
    if (!presenting) return;
    presenting = false;
    document.body.classList.remove(PRESENTING_CLASS);
    slides.forEach((s) => {
      s.classList.remove(CURRENT_CLASS);
      closeDetailOn(s);
    });
    slides = [];
  }

  function togglePresenter() {
    if (presenting) exitPresenter();
    else enterPresenter();
  }

  function currentSlide() {
    return slides[currentIdx];
  }

  function isDetailOpen() {
    const s = currentSlide();
    return !!(s && s.classList.contains(DETAIL_OPEN_CLASS));
  }

  function toggleDetail() {
    const s = currentSlide();
    if (!isExhibitSlide(s)) return;
    if (!hasDataTable(s)) return;
    if (isDetailOpen()) {
      closeDetailOn(s);
    } else {
      s.classList.add(DETAIL_OPEN_CLASS);
      const details = s.querySelector("details.data-table");
      if (details) details.setAttribute("open", "");
    }
  }

  function isTypingTarget(target) {
    if (!target) return false;
    const tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
  }

  document.addEventListener("keydown", (e) => {
    if (isTypingTarget(e.target)) return;

    if (e.key === "p" || e.key === "P") {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      e.preventDefault();
      togglePresenter();
      return;
    }

    if (!presenting) return;

    switch (e.key) {
      case "ArrowRight":
      case " ":
      case "Spacebar":
      case "PageDown":
        e.preventDefault();
        showSlide(currentIdx + 1);
        break;
      case "ArrowLeft":
      case "PageUp":
        e.preventDefault();
        showSlide(currentIdx - 1);
        break;
      case "Home":
        e.preventDefault();
        showSlide(0);
        break;
      case "End":
        e.preventDefault();
        showSlide(slides.length - 1);
        break;
      case "d":
      case "D":
        e.preventDefault();
        toggleDetail();
        break;
      case "Escape":
        e.preventDefault();
        if (isDetailOpen()) closeDetailOn(currentSlide());
        else exitPresenter();
        break;
      default:
        break;
    }
  });

  if (btnPresent) {
    btnPresent.addEventListener("click", () => {
      togglePresenter();
    });
  }
})();
