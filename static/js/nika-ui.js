/* Lightweight stand-in for Bootstrap JS: modal, collapse, dropdown. */
(() => {
  "use strict";

  const openModal = (el) => {
    if (!el) return;
    el.classList.add("is-open", "show");
    el.setAttribute("aria-hidden", "false");
  };
  const closeModal = (el) => {
    if (!el) return;
    el.classList.remove("is-open", "show");
    el.setAttribute("aria-hidden", "true");
  };

  window.NikaModal = {
    show: openModal,
    hide: closeModal,
  };

  document.addEventListener("click", (event) => {
    const modalBtn = event.target.closest("[data-bs-toggle='modal']");
    if (modalBtn) {
      event.preventDefault();
      openModal(document.querySelector(modalBtn.getAttribute("data-bs-target")));
      return;
    }
    const dismiss = event.target.closest("[data-bs-dismiss='modal']");
    if (dismiss) {
      closeModal(dismiss.closest(".modal"));
      return;
    }
    if (event.target.classList.contains("modal")) {
      closeModal(event.target);
      return;
    }

    const collapseBtn = event.target.closest("[data-bs-toggle='collapse']");
    if (collapseBtn) {
      event.preventDefault();
      const target = document.querySelector(collapseBtn.getAttribute("data-bs-target"));
      if (!target) return;
      const open = target.classList.toggle("show");
      collapseBtn.setAttribute("aria-expanded", open ? "true" : "false");
      return;
    }

    const dropBtn = event.target.closest("[data-bs-toggle='dropdown']");
    if (dropBtn) {
      event.preventDefault();
      dropBtn.closest(".dropdown")?.classList.toggle("is-open");
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
