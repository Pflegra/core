const toggle = document.querySelector(".nav-toggle");
const links = document.querySelector(".nav-links");

if (toggle && links) {
  toggle.addEventListener("click", () => {
    const open = links.dataset.open !== "true";
    links.dataset.open = String(open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Navigation schließen" : "Navigation öffnen");
  });

  links.addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      links.dataset.open = "false";
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "Navigation öffnen");
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      links.dataset.open = "false";
      toggle.setAttribute("aria-expanded", "false");
      toggle.focus();
    }
  });
}
