// Menú común: desplegables (clic, teclado y ratón), menú de móvil y marca de la sección activa.
(function () {
  "use strict";
  const barra = document.querySelector(".barra");
  if (!barra) return;
  const nav = barra.querySelector("nav");
  const botonMovil = barra.querySelector(".menu-movil");
  const grupos = [...barra.querySelectorAll(".grupo-menu")];
  const esMovil = () => window.matchMedia("(max-width:1100px)").matches;

  function cerrarGrupos(excepto) {
    grupos.forEach(g => {
      if (g === excepto) return;
      g.classList.remove("abierto");
      g.querySelector(".titulo-menu").setAttribute("aria-expanded", "false");
    });
  }
  function cerrarMovil() {
    if (!nav.classList.contains("abierto")) return;
    nav.classList.remove("abierto");
    botonMovil.setAttribute("aria-expanded", "false");
  }

  grupos.forEach(g => {
    const t = g.querySelector(".titulo-menu");
    t.addEventListener("click", () => {
      if (esMovil()) return;
      const abrir = !g.classList.contains("abierto");
      cerrarGrupos(g);
      g.classList.toggle("abierto", abrir);
      t.setAttribute("aria-expanded", String(abrir));
    });
  });
  botonMovil.addEventListener("click", () => {
    const abrir = !nav.classList.contains("abierto");
    nav.classList.toggle("abierto", abrir);
    botonMovil.setAttribute("aria-expanded", String(abrir));
  });
  // Al elegir una opción, se cierra todo
  barra.querySelectorAll("nav a").forEach(a => a.addEventListener("click", () => { cerrarGrupos(); cerrarMovil(); }));
  document.addEventListener("click", e => { if (!barra.contains(e.target)) { cerrarGrupos(); cerrarMovil(); } });
  document.addEventListener("keydown", e => {
    if (e.key !== "Escape") return;
    const abierto = barra.querySelector(".grupo-menu.abierto .titulo-menu");
    cerrarGrupos(); cerrarMovil();
    if (abierto) abierto.focus();
  });

  // Página activa (Primera semana, Profesiones...)
  const pagina = location.pathname.split("/").pop() || "index.html";
  const marcar = enlace => {
    barra.querySelectorAll("nav a.activo").forEach(a => { a.classList.remove("activo"); a.removeAttribute("aria-current"); });
    grupos.forEach(g => g.classList.remove("activo"));
    if (!enlace) return;
    enlace.classList.add("activo");
    enlace.setAttribute("aria-current", enlace.hash ? "location" : "page");
    const g = enlace.closest(".grupo-menu");
    if (g) g.classList.add("activo");
  };
  const enlaces = [...barra.querySelectorAll("nav a")];
  const dePagina = enlaces.find(a => !a.hash && a.pathname.split("/").pop() === pagina);
  if (dePagina) { marcar(dePagina); return; }

  // En la página principal: la sección visible marca su enlace y su grupo
  const conSeccion = enlaces.filter(a => a.hash && a.pathname === location.pathname && document.querySelector(a.hash));
  if (!conSeccion.length || !("IntersectionObserver" in window)) return;
  const obs = new IntersectionObserver(entradas => {
    entradas.forEach(e => {
      if (!e.isIntersecting) return;
      marcar(conSeccion.find(a => a.hash === "#" + e.target.id) || null);
    });
  }, { rootMargin: "-45% 0px -50% 0px" });
  conSeccion.forEach(a => obs.observe(document.querySelector(a.hash)));
  const inicio = document.getElementById("inicio");
  if (inicio) new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) marcar(null); }), { rootMargin: "-45% 0px -50% 0px" }).observe(inicio);
})();
