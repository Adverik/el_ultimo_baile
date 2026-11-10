#!/usr/bin/env python3
"""Catálogo de profesiones de WoW Forever desde la API de Blizzard (datos estáticos del juego).

Guarda en datos/catalogo.json todas las recetas de cada profesión, por categoría, con lo necesario
para el tooltip (reactivos, objeto fabricado y sus datos) y descarga los iconos a img/iconos/.
Es reanudable: lo que ya está en el catálogo no se vuelve a pedir. Tiene un tiempo máximo por ejecución.
Solo lectura (GET) y solo datos del juego: ningún dato de personas.
"""
import json, os, re, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from actualizar_blizzard import Blizzard, texto, leer, aviso  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
NS = os.environ.get("BLIZZARD_NS_ESTATICO", "static-forever-eu")
CATALOGO = RAIZ / "datos" / "catalogo.json"
ICONOS = RAIZ / "img" / "iconos"
LIMITE_SEGUNDOS = int(os.environ.get("LIMITE_SEGUNDOS", "4800"))
CALIDAD = {"LEGENDARY": "legendary", "ARTIFACT": "legendary", "EPIC": "epic", "RARE": "rare",
           "UNCOMMON": "uncommon", "COMMON": "common", "POOR": "poor"}


def guardar(cat):
    CATALOGO.parent.mkdir(exist_ok=True)
    CATALOGO.write_text(json.dumps(cat, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")


def ds(obj):
    """display_string de un campo de preview_item (o None)."""
    if isinstance(obj, dict):
        d = obj.get("display_string") or (obj.get("display") or {}).get("display_string")
        return texto(d, 120) if d else None
    return None


def datos_objeto(bz, item_id):
    st, it = bz.get(f"/data/wow/item/{item_id}", NS)
    if st != 200 or not it:
        return None
    pv = it.get("preview_item") or {}
    o = {"id": item_id, "n": texto(it.get("name"), 80), "q": CALIDAD.get((it.get("quality") or {}).get("type"), "common")}
    if it.get("level"): o["ilvl"] = it["level"]
    if it.get("required_level"): o["req"] = it["required_level"]
    if (pv.get("binding") or {}).get("name"): o["lig"] = texto(pv["binding"]["name"], 40)
    tipo = (pv.get("inventory_type") or {}).get("name")
    if tipo and (pv.get("inventory_type") or {}).get("type") not in ("NON_EQUIP",): o["ranura"] = texto(tipo, 30)
    sub = (pv.get("item_subclass") or {}).get("name")
    if sub: o["sub"] = texto(sub, 30)
    if ds(pv.get("container_slots")): o["slots"] = ds(pv["container_slots"])
    if ds(pv.get("armor")): o["arm"] = ds(pv["armor"])
    w = pv.get("weapon") or {}
    if ds(w.get("damage")): o["dano"] = ds(w["damage"])
    if ds(w.get("attack_speed")): o["vel"] = ds(w["attack_speed"])
    if ds(w.get("dps")): o["dps"] = ds(w["dps"])
    stats = [ds(s) for s in (pv.get("stats") or []) if ds(s)]
    if stats: o["stats"] = stats[:12]
    hech = [texto(s.get("description"), 240) for s in (pv.get("spells") or []) if s.get("description")]
    if hech: o["efectos"] = hech[:4]
    if ds((pv.get("requirements") or {}).get("level")) and "req" not in o:
        o["reqtxt"] = ds(pv["requirements"]["level"])
    sp = (pv.get("sell_price") or {}).get("display_strings") or {}
    if sp:
        o["venta"] = [sp.get("gold", "0"), sp.get("silver", "0"), sp.get("copper", "0")]
    o["ico"] = icono(bz, "item", item_id)
    return o


def icono(bz, tipo, ident):
    st, md = bz.get(f"/data/wow/media/{tipo}/{ident}", NS)
    for a in (md or {}).get("assets", []):
        url = str(a.get("value", ""))
        m = re.match(r"^https://render\.worldofwarcraft\.com/[\w-]+/icons/56/([\w-]+)\.jpg$", url)
        if a.get("key") == "icon" and m:
            nombre = m.group(1)
            ruta = ICONOS / f"{nombre}.jpg"
            if not ruta.exists():
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ElUltimoBaile-web"}), timeout=20) as r:
                        datos = r.read(200_000)
                    if datos[:3] == b"\xff\xd8\xff":
                        ICONOS.mkdir(parents=True, exist_ok=True)
                        ruta.write_bytes(datos)
                    else:
                        return None
                except Exception:  # noqa: BLE001
                    return None
            return nombre
    return None


def main():
    cid, sec = os.environ.get("BLIZZARD_CLIENT_ID", "").strip(), os.environ.get("BLIZZARD_CLIENT_SECRET", "").strip()
    if not cid or not sec:
        aviso("faltan BLIZZARD_CLIENT_ID / BLIZZARD_CLIENT_SECRET")
    bz = Blizzard(cid, sec)
    inicio = time.time()
    cat = leer(CATALOGO, {})
    cat.setdefault("profesiones", [])
    cat.setdefault("recetas", {})

    # 1) Estructura: profesiones -> niveles -> categorías -> recetas (siempre se refresca)
    st, idx = bz.get("/data/wow/profession/index", NS)
    profs = (idx or {}).get("professions") or []
    if st != 200 or not profs:
        aviso(f"no se pudo leer el índice de profesiones (HTTP {st})")
    estructura, por_receta = [], {}
    for p in profs:
        if not p.get("name") or not isinstance(p.get("id"), int):
            continue
        st, pr = bz.get(f"/data/wow/profession/{p['id']}", NS)
        ico = icono(bz, "profession", p["id"])
        for t in (pr or {}).get("skill_tiers") or []:
            st2, tier = bz.get(f"/data/wow/profession/{p['id']}/skill-tier/{t['id']}", NS)
            cats = []
            for c in (tier or {}).get("categories") or []:
                ids = [r["id"] for r in (c.get("recipes") or []) if isinstance(r.get("id"), int)]
                for r in c.get("recipes") or []:
                    if isinstance(r.get("id"), int):
                        por_receta[str(r["id"])] = (texto(r.get("name"), 80), texto(c.get("name"), 40))
                if ids:
                    cats.append({"nombre": texto(c.get("name"), 40), "recetas": ids})
            if cats and "DNT" not in str(t.get("name")):
                estructura.append({"id": p["id"], "tier": t["id"], "nombre": texto(t.get("name"), 30),
                                   "ico": ico, "categorias": cats})
    cat["profesiones"] = estructura
    print(f"Estructura: {len(estructura)} profesiones, {len(por_receta)} recetas")

    # 2) Detalle de cada receta (reanudable)
    nuevas = 0
    for rid, (nombre, categoria) in por_receta.items():
        if time.time() - inicio > LIMITE_SEGUNDOS:
            print("Tiempo máximo alcanzado: se seguirá en la próxima ejecución")
            break
        previa = cat["recetas"].get(rid)
        if previa and previa.get("ok"):
            previa["n"], previa["cat"] = nombre, categoria
            continue
        st, rec = bz.get(f"/data/wow/recipe/{rid}", NS)
        if st != 200 or not rec:
            continue
        d = {"n": nombre or texto(rec.get("name"), 80), "cat": categoria, "ok": 1}
        reac = [[texto((x.get("reagent") or {}).get("name"), 60), x.get("quantity", 1)] for x in (rec.get("reagents") or [])]
        if reac: d["reac"] = reac[:10]
        cq = (rec.get("crafted_quantity") or {})
        if cq.get("value") and cq["value"] != 1: d["cant"] = cq["value"]
        if rec.get("description"): d["desc"] = texto(rec["description"], 240)
        item = rec.get("crafted_item") or rec.get("alliance_crafted_item") or {}
        if isinstance(item.get("id"), int):
            o = datos_objeto(bz, item["id"])
            if o: d["obj"] = o
            d["ico"] = (o or {}).get("ico")
        if not d.get("ico"):
            d["ico"] = icono(bz, "recipe", rid)
        cat["recetas"][rid] = d
        nuevas += 1
        if nuevas % 100 == 0:
            guardar(cat)
            print(f"  {nuevas} recetas nuevas…")
    guardar(cat)
    hechas = sum(1 for r in cat["recetas"].values() if r.get("ok"))
    print(f"Catálogo: {hechas}/{len(por_receta)} recetas con detalle ({nuevas} nuevas en esta ejecución), "
          f"{len(list(ICONOS.glob('*.jpg'))) if ICONOS.exists() else 0} iconos")


if __name__ == "__main__":
    main()
