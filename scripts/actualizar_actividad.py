#!/usr/bin/env python3
"""Genera actividad.json (raids y botín) a partir de la API de wowaudit.

- Solo lectura (GET), clave en la cabecera Authorization, nunca en URL ni logs.
- Minimización: solo lo que enseña la web (raids: fecha, título, instancia,
  dificultad y nº de apuntados; botín: fecha, personaje y objeto).
- Si algo falla, no toca actividad.json y termina con error.
"""

import datetime
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "actividad.json"
BASE = (os.environ.get("WOWAUDIT_BASE_URL") or "https://api.wowaudit.com").strip().rstrip("/")
CLAVE = os.environ.get("WOWAUDIT_API_KEY", "").strip()
MAX_TXT = 80
N_RAIDS = 3
N_BOTIN = 12


def fallar(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def get(ruta):
    req = urllib.request.Request(
        f"{BASE}{ruta}",
        headers={"Authorization": f"Bearer {CLAVE}", "Accept": "application/json",
                 "User-Agent": "el-ultimo-baile-actividad/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            cuerpo = r.read(5 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as e:
        fallar(f"{ruta.split('?')[0]} respondió {e.code}")
    except urllib.error.URLError as e:
        fallar(f"no se pudo conectar ({e.reason})")
    if len(cuerpo) > 5 * 1024 * 1024:
        fallar("respuesta demasiado grande")
    try:
        return json.loads(cuerpo.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        fallar(f"{ruta.split('?')[0]} no devolvió JSON válido")


def txt(v):
    return "" if v is None else str(v).strip()[:MAX_TXT]


def primero(d, *rutas):
    """Devuelve el primer valor no vacío siguiendo rutas tipo 'item.name'."""
    for ruta in rutas:
        v = d
        for parte in ruta.split("."):
            v = v.get(parte) if isinstance(v, dict) else None
        if v not in (None, "", [], {}):
            return v
    return None


def raid_publica(r):
    return {
        "fecha": txt(r.get("date"))[:10],
        "titulo": txt(r.get("title")),
        "instancia": txt(r.get("instance")),
        "dificultad": txt(r.get("difficulty")),
        "apuntados": r.get("present_size") if isinstance(r.get("present_size"), int) else None,
    }


def main():
    if not CLAVE:
        fallar("falta el secreto WOWAUDIT_API_KEY")
    if not BASE.startswith("https://"):
        fallar("WOWAUDIT_BASE_URL debe empezar por https://")

    hoy = datetime.date.today().isoformat()

    # Raids
    datos = get("/v1/raids?include_past=true")
    raids = datos.get("raids") if isinstance(datos, dict) else datos
    if not isinstance(raids, list):
        fallar("formato inesperado en /v1/raids")
    raids = [r for r in raids if isinstance(r, dict) and txt(r.get("date"))]
    pasadas = sorted((r for r in raids if txt(r.get("date"))[:10] < hoy), key=lambda r: r["date"], reverse=True)
    futuras = sorted((r for r in raids if txt(r.get("date"))[:10] >= hoy), key=lambda r: r["date"])

    # Botín de la temporada actual
    botin = []
    periodo = get("/v1/period")
    temporada = primero(periodo, "current_season.id", "season_id") if isinstance(periodo, dict) else None
    if isinstance(temporada, int):
        historial = get(f"/v1/loot_history/{temporada}")
        items = historial.get("history_items") if isinstance(historial, dict) else historial
        for it in items if isinstance(items, list) else []:
            if not isinstance(it, dict):
                continue
            pj = primero(it, "character.name", "character_name", "name")
            objeto = primero(it, "item.name", "item_name", "item")
            fecha = primero(it, "awarded_at", "date", "created_at", "timestamp")
            if not pj or not objeto or isinstance(objeto, dict):
                continue
            botin.append({"fecha": txt(fecha)[:10], "personaje": txt(pj), "objeto": txt(objeto)})
        botin.sort(key=lambda b: b["fecha"], reverse=True)

    salida = {
        "proxima_raid": raid_publica(futuras[0]) if futuras else None,
        "ultimas_raids": [raid_publica(r) for r in pasadas[:N_RAIDS]],
        "botin": botin[:N_BOTIN],
    }
    nuevo = json.dumps(salida, ensure_ascii=False, indent=2) + "\n"
    actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
    if nuevo == actual:
        print("actividad.json sin cambios")
        return
    DESTINO.write_text(nuevo, encoding="utf-8")
    print(f"actividad.json actualizado ({len(salida['ultimas_raids'])} raids, botín: {len(botin)})")


if __name__ == "__main__":
    main()
