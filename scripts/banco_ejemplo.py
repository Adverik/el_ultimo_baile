#!/usr/bin/env python3
"""Genera banco.json con DATOS DE EJEMPLO para la maqueta del banco.

Los objetos, iconos y precios de vendedor son reales (salen del catálogo de Blizzard,
datos/catalogo.json). Los personajes, cantidades y movimientos son inventados y el
fichero lleva "ejemplo": true para que la web lo avise. Cuando haya datos reales, este
script se sustituye por el que lea la exportación del addon del banco.
"""
import json, random
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
cat = json.loads((RAIZ / "datos/catalogo.json").read_text())

objs = {}
for r in cat["recetas"].values():
    o = r.get("obj") or {}
    if o.get("id") and r.get("ico") and o["n"] not in objs:
        objs[o["n"]] = {**o, "ico": r["ico"]}

def cobre(v):
    if not v: return 0
    g, s, c = (int(x) for x in v)
    return g * 10000 + s * 100 + c

# (pestaña, icono de la pestaña, [(objeto, tamaño de pila, pilas)])
PESTANAS = [
    ("Consumibles de raid", "134821", [
        ("Frasco de poder supremo", 1, 6), ("Frasco de sabiduría destilada", 1, 5), ("Frasco de resistencia cromática", 1, 2),
        ("Poción de maná sublime", 5, 6), ("Elixir de la mangosta", 5, 4), ("Elixir de sangre de trol sublime", 5, 3),
        ("Elixir de poder de Escarcha", 5, 2), ("Venda de paño rúnico pesada", 20, 5), ("Sopa de pargo nocturno", 20, 2),
        ("Calamar a la parrilla", 20, 3), ("Lubina ahumada caliente", 20, 2), ("Piedra de afilar elemental", 10, 3),
        ("Aceite de maná inferior", 1, 4), ("Aceite de zahorí inferior", 1, 3), ("Abrillantador trol magnífico", 5, 2),
    ]),
    ("Materiales", "133221", [
        ("Lingote de torio", 20, 8), ("Lingote de veraplata", 20, 3), ("Lingote de mitril", 20, 5), ("Lingote Hierro Negro", 20, 1),
        ("Pellejo basto curado", 10, 4), ("Cuero grueso", 20, 6), ("Cuero basto", 20, 5), ("Cuero encantado", 20, 1),
        ("Esencia viva", 10, 2), ("Madeja de paño rúnico", 10, 6), ("Lingote de torio encantado", 20, 1),
    ]),
    ("Equipo y bolsas", "133652", [
        ("Bolsa de paño rúnico", 1, 4), ("Bolsa de tela lunar", 1, 1), ("Complemento para armadura del Núcleo", 1, 2),
        ("Robot de reparación de campo 74A", 1, 1), ("Muñeco-diana magistral", 1, 1),
    ]),
    ("Varios", "133713", [
        ("Granada de torio", 10, 4), ("Bomba Hierro Negro", 10, 2), ("Dinamita densa", 10, 3), ("Proyectiles de torio", 200, 3),
    ]),
]
NOMBRES = [("Aldric", "paladin"), ("Brannoc", "warrior"), ("Elowen", "druid"), ("Mirela", "priest"), ("Tavish", "rogue"),
           ("Isolde", "mage"), ("Orrin", "hunter"), ("Sabela", "warlock")]
PESO = [5, 9, 4, 7, 2, 6, 3, 1]

rnd = random.Random(42)
pestanas, todos = [], []
for nombre, ico, lista in PESTANAS:
    huecos = []
    for n, pila, pilas in lista:
        o = objs.get(n)
        if not o: continue
        item = {"id": o["id"], "n": o["n"], "q": o.get("q", "common"), "ico": o["ico"], "obj": {k: o[k] for k in o if k not in ("ico",)}, "venta": cobre(o.get("venta"))}
        todos.append(item)
        for _ in range(pilas):
            huecos.append({**{k: item[k] for k in ("id",)}, "cant": max(1, pila if rnd.random() < .75 else rnd.randint(1, pila))})
    pestanas.append({"nombre": nombre, "ico": ico, "huecos": huecos})

ahora = datetime(2026, 11, 10, 23, 0, tzinfo=timezone.utc)
registro = []
for _ in range(140):
    pj, clase = rnd.choices(NOMBRES, weights=PESO)[0]
    cuando = ahora - timedelta(days=rnd.uniform(0, 42), hours=rnd.uniform(0, 12))
    if rnd.random() < .22:
        registro.append({"t": cuando.isoformat(timespec="minutes"), "pj": pj, "clase": clase, "tipo": "deposito", "oro": rnd.choice([5, 10, 10, 20, 25, 50, 100]) * 10000})
    else:
        it = rnd.choice(todos)
        registro.append({"t": cuando.isoformat(timespec="minutes"), "pj": pj, "clase": clase, "tipo": "deposito", "id": it["id"], "cant": rnd.choice([1, 2, 5, 10, 20])})
for _ in range(18):
    pj, clase = rnd.choice(NOMBRES)
    it = rnd.choice(todos)
    cuando = ahora - timedelta(days=rnd.uniform(0, 42))
    registro.append({"t": cuando.isoformat(timespec="minutes"), "pj": pj, "clase": clase, "tipo": "retirada", "id": it["id"], "cant": rnd.choice([1, 2, 5])})
registro.sort(key=lambda e: e["t"], reverse=True)

datos = {
    "ejemplo": True,
    "actualizado": ahora.isoformat(timespec="minutes"),
    "oro": 1284 * 10000 + 37 * 100 + 12,
    "objetos": {str(i["id"]): {k: i[k] for k in ("n", "q", "ico", "venta", "obj")} for i in todos},
    "pestanas": pestanas,
    "registro": registro,
}
(RAIZ / "banco.json").write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")))
print(len(todos), "objetos,", sum(len(p["huecos"]) for p in pestanas), "huecos,", len(registro), "movimientos")
