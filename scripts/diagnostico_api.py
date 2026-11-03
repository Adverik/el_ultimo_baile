#!/usr/bin/env python3
"""Diagnóstico de la API de wowaudit: muestra SOLO la forma de las respuestas.

Imprime nombres de campos, tipos y longitudes de listas, nunca valores.
Sirve para saber cómo leer raids, botín y actividad sin exponer datos en los
registros públicos de GitHub Actions. Solo hace peticiones GET.
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE = (os.environ.get("WOWAUDIT_BASE_URL") or "https://api.wowaudit.com").strip().rstrip("/")
CLAVE = os.environ.get("WOWAUDIT_API_KEY", "").strip()


def get(ruta):
    req = urllib.request.Request(
        f"{BASE}{ruta}",
        headers={"Authorization": f"Bearer {CLAVE}", "Accept": "application/json",
                 "User-Agent": "el-ultimo-baile-diagnostico/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read(5 * 1024 * 1024).decode("utf-8-sig")), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__


def forma(dato, sangria=0, max_prof=5):
    pre = "  " * sangria
    if sangria > max_prof:
        print(f"{pre}…")
        return
    if isinstance(dato, dict):
        for k, v in dato.items():
            if isinstance(v, (dict, list)):
                etiqueta = f"lista[{len(v)}]" if isinstance(v, list) else "objeto"
                print(f"{pre}{k}: {etiqueta}")
                forma(v, sangria + 1, max_prof)
            else:
                print(f"{pre}{k}: {type(v).__name__}")
    elif isinstance(dato, list):
        if dato:
            print(f"{pre}[elemento 0 de {len(dato)}]")
            forma(dato[0], sangria + 1, max_prof)
    else:
        print(f"{pre}{type(dato).__name__}")


def mostrar(nombre, ruta):
    print(f"\n===== {nombre}  GET {ruta}")
    datos, error = get(ruta)
    if error:
        print(f"  error: {error}")
        return None
    forma(datos, 1)
    return datos


def main():
    if not CLAVE:
        sys.exit("Falta WOWAUDIT_API_KEY")

    periodo = mostrar("Periodo", "/v1/period")
    mostrar("Raids (próximas)", "/v1/raids")
    raids_pasadas = mostrar("Raids (con pasadas)", "/v1/raids?include_past=true")

    # Detalle de una raid, si hay alguna
    lista = raids_pasadas.get("raids") if isinstance(raids_pasadas, dict) else raids_pasadas
    if isinstance(lista, list) and lista and isinstance(lista[0], dict) and "id" in lista[0]:
        mostrar("Detalle de una raid", f"/v1/raids/{lista[0]['id']}")

    # Temporada y periodo para botín y actividad
    temporada = per = None
    if isinstance(periodo, dict):
        temporada = periodo.get("season_id") or (periodo.get("current_season") or {}).get("id")
        per = periodo.get("current_period") or periodo.get("period")
    print(f"\n(temporada encontrada: {'sí' if temporada else 'no'}, periodo encontrado: {'sí' if per else 'no'})")
    if temporada:
        mostrar("Historial de botín", f"/v1/loot_history/{temporada}")
        mostrar("Historial de botín (temporada anterior)", f"/v1/loot_history/{temporada - 1}")
    if per:
        mostrar("Actividad del periodo", f"/v1/historical_data?period={per}")
        mostrar("Actividad del periodo anterior", f"/v1/historical_data?period={per - 1}")
        mostrar("Actividad de hace dos periodos", f"/v1/historical_data?period={per - 2}")
    # Valores de estado y dificultad de las raids (solo valores distintos, son etiquetas, no datos personales)
    if isinstance(lista, list):
        estados = sorted({str(r.get("status")) for r in lista if isinstance(r, dict)})
        dific = sorted({str(r.get("difficulty")) for r in lista if isinstance(r, dict)})
        print(f"\n(estados de raid: {estados}; dificultades: {dific})")
    mostrar("Asistencia", "/v1/attendance")


if __name__ == "__main__":
    main()
