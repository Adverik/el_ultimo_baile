#!/usr/bin/env python3
"""Copia la web de la rama actual a prueba/ (versión para oficiales, no indexada).

Uso (desde la raíz del repo, en la rama con los cambios):  python3 scripts/prueba.py DESTINO
Los datos vivos (roster, actividad, profesiones...) se leen de la web real (../); los de
ejemplo (banco.json, loot.json) y comun/ se copian dentro de prueba/.
"""
import re, shutil, sys
from pathlib import Path

RAIZ = Path.cwd()
DEST = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "prueba"
PAGINAS = ["index.html", "primera-semana.html", "profesiones.html", "recetas.html", "banco.html", "loot.html"]
PROPIOS = ["banco.json", "loot.json"]
FRANJA = ('<div style="position:sticky;top:0;z-index:70;background:#d2a955;color:#1a1306;text-align:center;'
          'font:600 .8rem/1.4 Manrope,system-ui,sans-serif;letter-spacing:.06em;padding:7px 12px">'
          'Versión de prueba para oficiales · algunos datos son de ejemplo · '
          '<a href="https://lastdance.cp-0.es/" style="color:#1a1306">Ir a la web real</a></div>')

if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True)
shutil.copytree(RAIZ / "comun", DEST / "comun")
for f in PROPIOS:
    shutil.copy(RAIZ / f, DEST / f)
for nombre in PAGINAS:
    s = (RAIZ / nombre).read_text(encoding="utf-8")
    s = re.sub(r'(["\'(])(fonts|img)/', r'\1../\2/', s)
    s = s.replace('href="aviso-legal.html"', 'href="../aviso-legal.html"')
    s = re.sub(r'fetch\("(?!banco\.json|loot\.json|prioridad\.json)([a-z-]+\.json)"', r'fetch("../\1"', s)
    s = s.replace('fetch("profesiones/', 'fetch("../profesiones/')
    s = s.replace('<script src="comun/recetas.js">', '<script>window.BASE_ICONOS = "../img/iconos/";</script>\n<script src="comun/recetas.js">', 1)
    s = s.replace("<body>", "<body>\n" + FRANJA, 1)
    if 'name="robots"' not in s:
        s = s.replace("<head>", '<head>\n<meta name="robots" content="noindex, nofollow">', 1)
    (DEST / nombre).write_text(s, encoding="utf-8")
print("prueba lista en", DEST)
