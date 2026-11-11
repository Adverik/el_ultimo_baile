// Recetas: enlace a Wowhead (Forever, en castellano) con icono y tooltip propio con los datos de Blizzard.
// Todo con textContent: los nombres vienen de fuera. No carga nada de terceros (iconos servidos desde la web).
(function () {
  "use strict";
  const COLOR = { poor: "#9d9d9d", common: "#ffffff", uncommon: "#1eff00", rare: "#0070dd", epic: "#a335ee", legendary: "#ff8000" };
  const el = (tag, clase, texto) => {
    const e = document.createElement(tag);
    if (clase) e.className = clase;
    if (texto !== undefined && texto !== null) e.textContent = texto;
    return e;
  };
  const urlWowhead = r => r.obj && Number.isInteger(r.obj.id)
    ? "https://www.wowhead.com/forever/es/item=" + r.obj.id
    : "https://www.wowhead.com/forever/es/search?q=" + encodeURIComponent(r.n || "");

  let tip = null, ancla = null;
  function tooltip() {
    if (!tip) { tip = el("div", "tip-receta"); tip.setAttribute("role", "tooltip"); tip.hidden = true; document.body.append(tip); }
    return tip;
  }
  function contenido(r) {
    const t = tooltip();
    const o = r.obj || {};
    const cab = el("div", "tip-cab");
    if (r.ico) { const i = el("img"); i.src = (window.BASE_ICONOS || "img/iconos/") + r.ico + ".jpg"; i.alt = ""; i.width = 36; i.height = 36; cab.append(i); }
    const nom = el("div", "tip-nombre", r.n);
    nom.style.color = COLOR[r.q] || COLOR.common;
    cab.append(nom);
    const filas = [cab];
    if (r.desc) filas.push(el("div", "tip-desc", r.desc));
    if (Array.isArray(r.reac) && r.reac.length) {
      filas.push(el("div", "tip-sub", "Reactivos:"));
      filas.push(el("div", "tip-reac", r.reac.map(([n, c]) => n + (c > 1 ? " (" + c + ")" : "")).join(", ")));
    }
    if (o.n) {
      filas.push(el("div", "tip-sep"));
      // El nombre del objeto solo se repite si es distinto del de la receta
      if (o.n !== r.n || r.cant > 1) {
        const on = el("div", "tip-obj", o.n + (r.cant > 1 ? " ×" + r.cant : ""));
        on.style.color = COLOR[o.q] || COLOR.common;
        filas.push(on);
      }
      if (o.ilvl) filas.push(el("div", "tip-ilvl", "Nivel de objeto " + o.ilvl));
      if (o.lig) filas.push(el("div", "", o.lig));
      if (o.ranura || o.sub) {
        const f = el("div", "tip-dos"); f.append(el("span", "", o.ranura || ""), el("span", "", o.sub || "")); filas.push(f);
      }
      if (o.dano) { const f = el("div", "tip-dos"); f.append(el("span", "", o.dano), el("span", "", o.vel || "")); filas.push(f); }
      if (o.dps) filas.push(el("div", "", o.dps));
      if (o.arm) filas.push(el("div", "", o.arm));
      if (o.slots) filas.push(el("div", "", o.slots));
      (o.stats || []).forEach(s => filas.push(el("div", "tip-stat", s)));
      (o.efectos || []).forEach(s => filas.push(el("div", "tip-efecto", s)));
      if (o.req) filas.push(el("div", "", "Requiere nivel " + o.req));
      else if (o.reqtxt) filas.push(el("div", "", o.reqtxt));
      if (Array.isArray(o.venta) && o.venta.some(v => String(v) !== "0")) {
        const f = el("div", "tip-venta", "Precio de venta: ");
        [["oro", o.venta[0]], ["plata", o.venta[1]], ["cobre", o.venta[2]]].forEach(([c, v]) => {
          if (String(v) !== "0") { const s = el("span", "moneda " + c, String(v)); f.append(s, " "); }
        });
        filas.push(f);
      }
    }
    filas.push(el("div", "tip-pie", "Clic para abrir en Wowhead"));
    t.replaceChildren(...filas);
  }
  function colocar(a) {
    const t = tooltip(), r = a.getBoundingClientRect();
    t.hidden = false;
    const w = t.offsetWidth, h = t.offsetHeight;
    let x = r.left, y = r.bottom + 8;
    if (x + w > innerWidth - 8) x = innerWidth - w - 8;
    if (y + h > innerHeight - 8) y = Math.max(8, r.top - h - 8);
    t.style.left = Math.max(8, x) + "px";
    t.style.top = y + "px";
  }
  function mostrar(a) { ancla = a; contenido(a._receta); colocar(a); }
  function ocultar() { if (tip) tip.hidden = true; ancla = null; }
  window.addEventListener("scroll", () => { if (ancla) colocar(ancla); }, { passive: true });
  document.addEventListener("keydown", e => { if (e.key === "Escape") ocultar(); });
  document.addEventListener("click", e => { if (ancla && !ancla.contains(e.target)) ocultar(); });

  // enlaceReceta(receta) -> <a> con icono y nombre del color de su calidad, enlace a Wowhead y tooltip
  // opciones.icono: solo el icono (con la cantidad encima si se da opciones.cantidad), para cuadrículas como la del banco
  window.enlaceReceta = function (r, opciones) {
    const op = opciones || {};
    const a = el("a", op.icono ? "ranura-enlace" : "receta-enlace");
    a.href = urlWowhead(r);
    a.target = "_blank";
    a.rel = "noopener";
    a._receta = r;
    if (r.ico) { const i = el("img"); i.src = (window.BASE_ICONOS || "img/iconos/") + r.ico + ".jpg"; i.alt = ""; i.width = 24; i.height = 24; i.loading = "lazy"; a.append(i); }
    else a.append(el("span", "sin-icono"));
    if (op.icono) {
      a.style.setProperty("--q", COLOR[r.q] || COLOR.common);
      a.setAttribute("aria-label", r.n + (op.cantidad > 1 ? " ×" + op.cantidad : ""));
      if (op.cantidad > 1) a.append(el("span", "ranura-cant", String(op.cantidad)));
    } else {
      const n = el("span", "receta-nombre", r.n);
      n.style.color = COLOR[r.q] || COLOR.common;
      a.append(n);
    }
    a.addEventListener("mouseenter", () => mostrar(a));
    a.addEventListener("mouseleave", ocultar);
    a.addEventListener("focus", () => mostrar(a));
    a.addEventListener("blur", ocultar);
    // En pantallas táctiles: el primer toque enseña el tooltip, el segundo abre Wowhead
    a.addEventListener("click", e => {
      if (window.matchMedia("(hover: none)").matches && ancla !== a) { e.preventDefault(); mostrar(a); }
    });
    return a;
  };
  window.COLOR_CALIDAD = COLOR;
})();
