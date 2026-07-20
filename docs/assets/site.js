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

const lightbox = document.querySelector("#lightbox");
const lightboxImage = document.querySelector("#lightbox-image");
const lightboxClose = document.querySelector(".lightbox-close");
let lightboxTrigger = null;

function closeLightbox() {
  if (!lightbox || !lightboxImage) return;
  lightbox.hidden = true;
  lightboxImage.removeAttribute("src");
  lightboxImage.alt = "";
  document.body.style.overflow = "";
  if (lightboxTrigger) lightboxTrigger.focus();
}

document.querySelectorAll("[data-lightbox-src]").forEach((trigger) => {
  trigger.addEventListener("click", () => {
    if (!lightbox || !lightboxImage) return;
    lightboxTrigger = trigger;
    lightboxImage.src = trigger.dataset.lightboxSrc;
    lightboxImage.alt = trigger.dataset.lightboxAlt || "";
    lightbox.hidden = false;
    document.body.style.overflow = "hidden";
    lightboxClose?.focus();
  });
});

lightboxClose?.addEventListener("click", closeLightbox);
lightbox?.addEventListener("click", (event) => {
  if (event.target === lightbox) closeLightbox();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && lightbox && !lightbox.hidden) closeLightbox();
});
