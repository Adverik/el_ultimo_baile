#!/usr/bin/env python3
"""Actualiza roster.json a partir de la API de wowaudit.

- Solo lectura: hace un único GET a /v1/characters.
- La clave llega por la variable de entorno WOWAUDIT_API_KEY (GitHub Secret) y viaja
  solo en la cabecera Authorization, nunca en la URL ni en los logs.
- Minimización de datos: al roster.json público solo pasan nombre, clase y rol.
- Si algo falla (red, formato, roster vacío), no toca roster.json y termina con error.
- Sin dependencias externas: solo librería estándar de Python.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "roster.json"
URL_POR_DEFECTO = "https://api.wowaudit.com"
TIMEOUT_SEGUNDOS = 30
MAX_BYTES = 2 * 1024 * 1024  # 2 MiB: un roster no debería acercarse a esto
MAX_LONGITUD_TEXTO = 40


def fallar(mensaje: str) -> None:
    print(f"ERROR: {mensaje}", file=sys.stderr)
    sys.exit(1)


def texto_limpio(valor) -> str:
    """Convierte a texto, quita espacios y recorta. Nada de HTML: la web lo pinta con textContent."""
    if valor is None:
        return ""
    texto = str(valor).strip()
    return texto[:MAX_LONGITUD_TEXTO]


def main() -> None:
    clave = os.environ.get("WOWAUDIT_API_KEY", "").strip()
    if not clave:
        fallar("falta el secreto WOWAUDIT_API_KEY")

    base = (os.environ.get("WOWAUDIT_BASE_URL") or URL_POR_DEFECTO).strip().rstrip("/")
    if not base.startswith("https://"):
        fallar("WOWAUDIT_BASE_URL debe empezar por https://")

    peticion = urllib.request.Request(
        f"{base}/v1/characters",
        headers={
            "Authorization": f"Bearer {clave}",
            "Accept": "application/json",
            "User-Agent": "el-ultimo-baile-roster/1.0",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(peticion, timeout=TIMEOUT_SEGUNDOS) as respuesta:
            cuerpo = respuesta.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        fallar(f"la API respondió {e.code}")  # sin cuerpo ni cabeceras: no queremos ecos de la clave
    except urllib.error.URLError as e:
        fallar(f"no se pudo conectar con la API ({e.reason})")

    if len(cuerpo) > MAX_BYTES:
        fallar("respuesta demasiado grande")

    try:
        datos = json.loads(cuerpo.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        fallar("la respuesta no es JSON válido")

    # La API devuelve una lista; por si acaso, aceptamos también {"characters": [...]}
    if isinstance(datos, dict):
        datos = datos.get("characters", datos.get("data"))
    if not isinstance(datos, list):
        fallar("formato inesperado: se esperaba una lista de personajes")

    roster = []
    for pj in datos:
        if not isinstance(pj, dict):
            continue
        nombre = texto_limpio(pj.get("name"))
        if not nombre:
            continue
        roster.append(
            {
                "name": nombre,
                "class": texto_limpio(pj.get("class")),
                "role": texto_limpio(pj.get("role")),
            }
        )

    if not roster:
        fallar("la API devolvió un roster vacío; no se sobrescribe roster.json")

    roster.sort(key=lambda p: p["name"].casefold())
    nuevo = json.dumps(roster, ensure_ascii=False, indent=2) + "\n"

    actual = DESTINO.read_text(encoding="utf-8-sig") if DESTINO.exists() else ""
    if actual == nuevo:
        print(f"Sin cambios ({len(roster)} personajes).")
        return

    DESTINO.write_text(nuevo, encoding="utf-8")
    print(f"roster.json actualizado ({len(roster)} personajes).")


if __name__ == "__main__":
    main()
