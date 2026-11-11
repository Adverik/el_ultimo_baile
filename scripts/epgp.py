#!/usr/bin/env python3
"""Calcula la tabla de prioridad EPGP a partir del registro de la raid.

Entrada:
  loot.json                 valores del sistema (EP por concepto, GP por ranura y respuesta, desgaste...)
  datos/botin/registro.csv  una línea por cosa que pasa en raid, en cualquier orden:
      fecha,pj,clase,concepto,ranura,respuesta,calidad,motivo
      2026-12-09T22:00,Hyo,warrior,noche,,,,
      2026-12-09T22:41,Hyo,warrior,objeto,Abalorio,Gran mejora,epic,
  concepto = una clave de "ep" en loot.json (noche, puntual, jefe_nuevo, banquillo, media) u "objeto".
  banquillo y media dan el porcentaje indicado del EP de "noche".

Salida:
  prioridad.json  EP, GP y PR de cada personaje, y los últimos repartos. La web lo lee si existe.

El registro lo rellenará el robot a partir de la asistencia (Warcraft Logs o wowaudit) y del
historial que exporta el addon de consejo. Se recalcula siempre desde cero: si algo se corrige
en el CSV, la tabla sale bien sola.
"""
import csv, json, sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
MADRID = ZoneInfo("Europe/Madrid")


def valor_ep(cfg, concepto):
    ep = {e["clave"]: e["valor"] for e in cfg["ep"]}
    v = ep.get(concepto)
    if isinstance(v, str) and v.endswith("%"):
        return ep["noche"] * float(v[:-1]) / 100
    return float(v or 0)


def valor_gp(cfg, ranura, respuesta, calidad):
    r = next((x["mult"] for x in cfg["ranuras"] if x["texto"] == ranura), None)
    p = next((x["mult"] for x in cfg["respuestas"] if x["texto"] == respuesta), None)
    if r is None or p is None:
        raise ValueError(f"ranura o respuesta desconocida: {ranura!r} / {respuesta!r}")
    return cfg["gp_base"] * r * p * (cfg["calidad_rara"] if calidad == "rare" else 1)


def viernes_entre(desde, hasta):
    """Momentos de desgaste (viernes 06:00, hora de Madrid) en (desde, hasta]."""
    d = desde.astimezone(MADRID).replace(hour=6, minute=0, second=0, microsecond=0)
    d += timedelta(days=(4 - d.weekday()) % 7)
    if d <= desde:
        d += timedelta(days=7)
    while d <= hasta:
        yield d
        d += timedelta(days=7)


def calcular(cfg, filas, ahora):
    filas = sorted(filas, key=lambda f: f["fecha"])
    pjs, repartos = {}, []
    reloj = filas[0]["fecha"] if filas else ahora
    d = cfg["decay"]

    def desgastar(hasta):
        nonlocal reloj
        for _ in viernes_entre(reloj, hasta):
            for p in pjs.values():
                p["ep"] *= 1 - d
                p["gp"] *= 1 - d
        reloj = max(reloj, hasta)

    for f in filas:
        desgastar(f["fecha"])
        p = pjs.setdefault(f["pj"], {"pj": f["pj"], "clase": f["clase"], "ep": 0.0, "gp": 0.0})
        if f["concepto"] == "objeto":
            gp = valor_gp(cfg, f["ranura"], f["respuesta"], f["calidad"])
            p["gp"] += gp
            repartos.append({"fecha": f["fecha"].isoformat(timespec="minutes"), "pj": f["pj"], "clase": f["clase"],
                             "ranura": f["ranura"], "respuesta": f["respuesta"], "gp": round(gp), "motivo": f["motivo"]})
        else:
            p["ep"] += valor_ep(cfg, f["concepto"])
    desgastar(ahora)
    base = cfg["gp_base"]
    tabla = [{"pj": p["pj"], "clase": p["clase"], "ep": round(p["ep"]), "gp": round(base + p["gp"])} for p in pjs.values()]
    tabla.sort(key=lambda x: x["ep"] / x["gp"], reverse=True)
    return tabla, repartos[::-1][:30]


def leer(ruta):
    filas = []
    with open(ruta, newline="", encoding="utf-8") as fh:
        for f in csv.DictReader(fh):
            f = {k: (v or "").strip() for k, v in f.items()}
            fecha = datetime.fromisoformat(f["fecha"])
            f["fecha"] = fecha if fecha.tzinfo else fecha.replace(tzinfo=MADRID)
            filas.append(f)
    return filas


def main():
    cfg = json.loads((RAIZ / "loot.json").read_text())
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "datos/botin/registro.csv"
    if not ruta.exists():
        print("Sin registro todavía:", ruta)
        return
    ahora = datetime.now(MADRID)
    tabla, repartos = calcular(cfg, leer(ruta), ahora)
    salida = Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "prioridad.json"
    salida.write_text(json.dumps({"actualizado": ahora.isoformat(timespec="minutes"), "filas": tabla, "repartos": repartos},
                                 ensure_ascii=False, indent=1))
    print(len(tabla), "personajes,", len(repartos), "repartos ->", salida)


if __name__ == "__main__":
    main()
