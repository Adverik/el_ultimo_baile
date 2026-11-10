#!/usr/bin/env python3
"""Escribe la misma barra de navegación en todas las páginas.

Para añadir una página o sección al menú, edítala en MENU y ejecuta:  python3 scripts/menu.py
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = ["index.html", "primera-semana.html", "profesiones.html", "recetas.html", "banco.html"]
DISCORD = "https://discord.gg/mdKr9CPTTM"

# Enlaces directos (secciones de base) y desplegables (temas que tendrán más cosas dentro).
# FIJOS: en pantallas estrechas se quedan siempre a la vista, junto al botón Menú.
FIJOS = ["Inicio", "La hermandad", "Primera semana"]
# Desplegable: (título, [(texto, enlace, descripción, etiqueta o None), ...])
MENU = [
    ("Inicio", "./#inicio"),
    ("La hermandad", "./#hermandad"),
    ("Raid", [
        ("Noches de raid", "./#raids", "Horario y lo que pedimos", None),
        ("Loot", "./#botin", "Cómo se reparte el botín", "En revisión"),
        ("Actividad", "./#actividad", "Próxima raid y últimas noches", None),
        ("Raiders", "./#raiders", "El roster actual, por clase", None),
    ]),
    ("Reclutamiento", "./#reclutamiento"),
    ("Primera semana", "primera-semana.html"),
    ("Recursos", [
        ("Profesiones", "profesiones.html", "Quién sabe hacer qué, y las recetas raras y épicas", "Nuevo"),
        ("Banco", "banco.html", "Lo que guarda la hermandad y cómo pedirlo", "En construcción"),
    ]),
]

ESCUDO = '''<svg width="30" height="34" viewBox="0 0 28 32" aria-hidden="true">
        <path d="M14 1 L27 5 V15 C27 23 21 28.5 14 31 C7 28.5 1 23 1 15 V5 Z" fill="#101218" stroke="#D2A955" stroke-width="1.5"/>
        <path d="M9 22 C9 15 19 15 19 9" stroke="#D2A955" stroke-width="1.6" fill="none" stroke-linecap="round"/>
        <path d="M19 22 C19 15 9 15 9 9" stroke="#ECE6D6" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      </svg>'''


def cabecera():
    grupos = []
    for i, (titulo, destino) in enumerate(MENU):
        if isinstance(destino, str):
            fijo = " fijo" if titulo in FIJOS else ""
            grupos.append(f'        <li class="item-menu{fijo}"><a class="enlace-menu" href="{destino}">{titulo}</a></li>')
            continue
        items = []
        for texto, href, desc, etiqueta in destino:
            et = f' <span class="etiqueta-menu">{etiqueta}</span>' if etiqueta else ""
            items.append(f'            <li><a href="{href}"><span class="t">{texto}{et}</span><span class="d">{desc}</span></a></li>')
        grupos.append(f'''        <li class="grupo-menu">
          <button class="titulo-menu" type="button" aria-expanded="false" aria-controls="sub-{i}">{titulo}</button>
          <ul class="submenu" id="sub-{i}">
{chr(10).join(items)}
          </ul>
        </li>''')
    return f'''<header class="barra">
  <div class="envoltura fila1">
    <a class="marca" href="./#inicio">
      {ESCUDO}
      El Último Baile
    </a>
    <ul class="rapidos">
{chr(10).join(f'      <li><a class="enlace-menu" href="{d}">{t}</a></li>' for t, d in MENU if isinstance(d, str) and t in FIJOS)}
    </ul>
    <button class="menu-movil" type="button" aria-expanded="false" aria-controls="menu-principal"><span class="rayas" aria-hidden="true"></span><span class="texto-menu">Menú</span></button>
    <nav id="menu-principal" aria-label="Principal">
      <ul class="menu">
{chr(10).join(grupos)}
      </ul>
    </nav>
    <a class="boton" href="{DISCORD}" rel="noopener">Únete</a>
  </div>
</header>'''


def main():
    nueva = cabecera()
    for nombre in PAGINAS:
        ruta = RAIZ / nombre
        s = ruta.read_text(encoding="utf-8")
        i, j = s.index('<header class="barra">'), s.index("</header>") + len("</header>")
        s = s[:i] + nueva + s[j:]
        if 'href="comun/menu.css"' not in s:
            s = s.replace("<style>", '<link rel="stylesheet" href="comun/menu.css">\n<style>', 1)
        if 'src="comun/menu.js"' not in s:
            s = s.replace("</body>", '<script src="comun/menu.js" defer></script>\n</body>', 1)
        ruta.write_text(s, encoding="utf-8")
        print("menú escrito en", nombre)


if __name__ == "__main__":
    main()
