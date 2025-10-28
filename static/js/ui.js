// static/js/ui.js
document.addEventListener("DOMContentLoaded", () => {
  // navegación lateral
  const navButtons = document.querySelectorAll("[data-nav]");
  const panels = document.querySelectorAll("[data-panel]");

  const show = (name) => {
    panels.forEach(p => p.classList.toggle("hidden", p.dataset.panel !== name));
    navButtons.forEach(b => b.classList.toggle("active", b.dataset.nav === name));
    // evita que el navegador “ensucie” la URL (nada de "/?")
    history.replaceState(null, "", "/");
  };

  navButtons.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();            // clave para no navegar a "/?"
      const target = btn.dataset.nav;
      if (target) show(target);
    });
  });

  // Personalizar (abre/cierra)
  const personalizeBtn = document.getElementById("btn-personalizar");
  const personalizePanel = document.getElementById("personalizar");
  const closeBtn = document.getElementById("btn-cerrar-personalizar");
  if (personalizeBtn && personalizePanel) {
    personalizeBtn.addEventListener("click", (e) => {
      e.preventDefault();            // evita saltos de página
      personalizePanel.classList.toggle("hidden");
    });
  }
  if (closeBtn && personalizePanel) {
    closeBtn.addEventListener("click", (e) => {
      e.preventDefault();
      personalizePanel.classList.add("hidden");
    });
  }

  // abre por defecto “chat”
  const first = panels[0];
  if (first && first.classList.contains("hidden")) {
    show(first.dataset.panel);
  }
});
