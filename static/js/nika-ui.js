/* Lightweight UI: modal, collapse, dropdown (no Bootstrap). */
(() => {
  "use strict";

  const openModal = (el) => {
    if (!el) return;
    el.classList.add("is-open");
    el.setAttribute("aria-hidden", "false");
  };
  const closeModal = (el) => {
    if (!el) return;
    el.classList.remove("is-open");
    el.setAttribute("aria-hidden", "true");
  };

  window.NikaModal = {
    show: openModal,
    hide: closeModal,
  };

  const toggleTarget = (btn, attr) => {
    const selector = btn.getAttribute(attr) || btn.getAttribute("data-nika-target");
    return selector ? document.querySelector(selector) : null;
  };

  document.addEventListener("click", (event) => {
    const toggleBtn = event.target.closest("[data-nika-toggle]");
    if (toggleBtn) {
      const kind = toggleBtn.getAttribute("data-nika-toggle");
      if (kind === "modal") {
        event.preventDefault();
        openModal(toggleTarget(toggleBtn, "data-nika-target"));
        return;
      }
      if (kind === "collapse") {
        event.preventDefault();
        const target = toggleTarget(toggleBtn, "data-nika-target");
        if (!target) return;
        const open = target.classList.toggle("is-open");
        toggleBtn.setAttribute("aria-expanded", open ? "true" : "false");
        return;
      }
      if (kind === "dropdown") {
        event.preventDefault();
        toggleBtn.closest(".dropdown")?.classList.toggle("is-open");
        return;
      }
    }

    const dismiss = event.target.closest("[data-nika-dismiss='modal']");
    if (dismiss) {
      closeModal(dismiss.closest(".modal"));
      return;
    }
    if (event.target.classList.contains("modal")) {
      closeModal(event.target);
      return;
    }

    if (!event.target.closest(".dropdown")) {
      document.querySelectorAll(".dropdown.is-open").forEach((el) => el.classList.remove("is-open"));
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    document.querySelectorAll(".modal.is-open").forEach((el) => closeModal(el));
  });
})();
