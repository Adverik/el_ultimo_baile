#!/usr/bin/env python3
"""Escribe la misma barra de navegación en todas las páginas.

Para añadir una página o sección al menú, edítala en MENU y ejecuta:  python3 scripts/menu.py
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = ["index.html", "primera-semana.html", "profesiones.html"]
DISCORD = "https://discord.gg/mdKr9CPTTM"

MENU = [
    ("La hermandad", [("Quiénes somos", "./#hermandad"), ("Raids", "./#raids"), ("Loot", "./#botin"),
                      ("Actividad", "./#actividad"), ("Raiders", "./#raiders")]),
    ("Reclutamiento", [("A quién buscamos", "./#reclutamiento"), ("Tu primera semana", "primera-semana.html")]),
    ("Recursos", [("Profesiones", "profesiones.html")]),
]

ESCUDO = '''<svg width="30" height="34" viewBox="0 0 28 32" aria-hidden="true">
        <path d="M14 1 L27 5 V15 C27 23 21 28.5 14 31 C7 28.5 1 23 1 15 V5 Z" fill="#101218" stroke="#D2A955" stroke-width="1.5"/>
        <path d="M9 22 C9 15 19 15 19 9" stroke="#D2A955" stroke-width="1.6" fill="none" stroke-linecap="round"/>
        <path d="M19 22 C19 15 9 15 9 9" stroke="#ECE6D6" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      </svg>'''


def cabecera():
    grupos = []
    for i, (titulo, enlaces) in enumerate(MENU):
        items = "\n".join(f'            <li><a href="{href}">{texto}</a></li>' for texto, href in enlaces)
        grupos.append(f'''        <li class="grupo-menu">
          <button class="titulo-menu" type="button" aria-expanded="false" aria-controls="sub-{i}">{titulo}</button>
          <ul class="submenu" id="sub-{i}">
{items}
          </ul>
        </li>''')
    return f'''<header class="barra">
  <div class="envoltura fila1">
    <a class="marca" href="./#inicio">
      {ESCUDO}
      El Último Baile
    </a>
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
