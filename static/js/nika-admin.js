/* Nika Fit enhancements layered on top of AdminLTE 4.2.0. */
(() => {
  "use strict";

  const body = document.body;
  if (!body.classList.contains("nika-admin")) return;

  const storageKey = "nika.sidebar.collapsed";
  const desktop = window.matchMedia("(min-width: 992px)");

  const applyStoredSidebarState = () => {
    if (!desktop.matches) return;
    const collapsed = localStorage.getItem(storageKey) === "1";
    body.classList.toggle("sidebar-collapse", collapsed);
    body.classList.toggle("sidebar-open", !collapsed);
  };

  applyStoredSidebarState();

  document.querySelectorAll('[data-lte-toggle="sidebar"]').forEach((toggle) => {
    toggle.addEventListener("click", () => {
      window.setTimeout(() => {
        if (!desktop.matches) return;
        localStorage.setItem(
          storageKey,
          body.classList.contains("sidebar-collapse") ? "1" : "0",
        );
      }, 50);
    });
  });

  document.querySelectorAll(".app-content table.table").forEach((table) => {
    if (table.parentElement?.classList.contains("table-responsive")) return;
    const wrapper = document.createElement("div");
    wrapper.className = "table-responsive";
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
  });

  document.querySelectorAll(".flash").forEach((flash) => {
    flash.setAttribute("role", "status");
  });

  document.querySelectorAll(".sidebar-menu .nav-link.active").forEach((link) => {
    link.setAttribute("aria-current", "page");
    link.closest(".nav-treeview")?.closest(".nav-item")?.classList.add("menu-open");
  });

  document.querySelectorAll(".js-row-link[data-href]").forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target.closest("a, button, input, select, label")) return;
      window.location.href = row.getAttribute("data-href");
    });
  });

  document.querySelectorAll("details[data-open-xl]").forEach((el) => {
    if (window.matchMedia("(min-width: 1200px)").matches) el.open = true;
  });

  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const sel = btn.getAttribute("data-copy");
      const field = sel ? document.querySelector(sel) : null;
      if (!field) return;
      const value = field.value || field.textContent || "";
      try {
        await navigator.clipboard.writeText(value);
        btn.textContent = "Скопировано";
        window.setTimeout(() => {
          btn.textContent = "Копировать";
        }, 1600);
      } catch (_err) {
        field.focus();
        field.select?.();
      }
    });
  });

  desktop.addEventListener?.("change", applyStoredSidebarState);
})();
