#!/usr/bin/env python3
"""Datos de la hermandad desde la API oficial de Blizzard (WoW Forever).

Genera:
  - nombres.json      nombre -> "Nombre Apellido" (para mostrar el nombre completo de los raiders)
  - profesiones.json  artesanos (toda la hermandad) y recetas agrupadas por calidad

Claves: BLIZZARD_CLIENT_ID / BLIZZARD_CLIENT_SECRET (GitHub Secrets).
Solo lectura (GET). Minimización: solo nombre, apellido, clase, profesiones, niveles y recetas.
La calidad de cada receta se guarda en datos/recetas_cache.json para no volver a pedirla.
Si Blizzard falla, no toca los ficheros y no rompe el robot.
"""
import base64, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
API = "https://eu.api.blizzard.com"
NS_PERFIL = os.environ.get("BLIZZARD_NS_PERFIL", "profile-forever-eu")
NS_ESTATICO = os.environ.get("BLIZZARD_NS_ESTATICO", "static-forever-eu")
GREMIO = "el-%C3%BAltimo-baile"
LOCALE = "es_ES"
CACHE = RAIZ / "datos" / "recetas_cache.json"
MAX_RECETAS_NUEVAS = 800          # tope de consultas nuevas por ejecución
CLASES = {1: "warrior", 2: "paladin", 3: "hunter", 4: "rogue", 5: "priest", 6: "deathknight",
          7: "shaman", 8: "mage", 9: "warlock", 10: "monk", 11: "druid"}
# Blizzard devuelve las profesiones de Forever en inglés aunque se pida es_ES
PROF_ES = {"Alchemy": "Alquimia", "Blacksmithing": "Herrería", "Enchanting": "Encantamiento", "Engineering": "Ingeniería",
           "Leatherworking": "Peletería", "Tailoring": "Sastrería", "Herbalism": "Herboristería", "Mining": "Minería",
           "Skinning": "Desuello", "Cooking": "Cocina", "First Aid": "Primeros auxilios", "Fishing": "Pesca"}
CALIDAD = {"LEGENDARY": "legendary", "EPIC": "epic", "RARE": "rare", "UNCOMMON": "uncommon",
           "COMMON": "common", "POOR": "common", "ARTIFACT": "legendary"}


def aviso(msg):
    print(f"AVISO: {msg}", file=sys.stderr)
    sys.exit(0)


def texto(v, largo=60):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:largo]


class Blizzard:
    def __init__(self, cid, sec):
        auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
        st, d = self._http("https://oauth.battle.net/token", {"Authorization": f"Basic {auth}",
                           "Content-Type": "application/x-www-form-urlencoded"}, b"grant_type=client_credentials")
        if not d or "access_token" not in d:
            aviso(f"no se pudo obtener el token de Blizzard (HTTP {st})")
        self.h = {"Authorization": f"Bearer {d['access_token']}", "Accept": "application/json"}

    @staticmethod
    def _http(url, headers, data=None):
        for intento in range(3):
            req = urllib.request.Request(url, data=data, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    return r.status, json.loads(r.read(4 * 1024 * 1024))
            except urllib.error.HTTPError as e:
                if e.code == 429 and intento < 2:
                    time.sleep(2 + intento * 3); continue
                return e.code, None
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                if intento < 2:
                    time.sleep(1); continue
                return type(e).__name__, None
        return "reintentos", None

    def get(self, ruta, ns):
        sep = "&" if "?" in ruta else "?"
        time.sleep(0.03)
        return self._http(f"{API}{ruta}{sep}namespace={ns}&locale={LOCALE}", self.h)


def leer(ruta, defecto):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def escribir_si_cambia(ruta, datos, campos_comparar=None):
    actual = leer(ruta, None)
    comparar = (lambda d: {k: d.get(k) for k in campos_comparar}) if campos_comparar else (lambda d: d)
    if isinstance(actual, dict) and isinstance(datos, dict) and comparar(actual) == comparar(datos):
        return False
    if actual == datos:
        return False
    Path(ruta).write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main():
    cid, sec = os.environ.get("BLIZZARD_CLIENT_ID", "").strip(), os.environ.get("BLIZZARD_CLIENT_SECRET", "").strip()
    if not cid or not sec:
        aviso("faltan BLIZZARD_CLIENT_ID / BLIZZARD_CLIENT_SECRET")
    bz = Blizzard(cid, sec)

    st, g = bz.get(f"/data/wow/guild/{GREMIO}/roster", NS_PERFIL)
    miembros = (g or {}).get("members") or []
    if st != 200 or not miembros:
        aviso(f"no se pudo leer el roster de la hermandad (HTTP {st})")

    raiders = {texto(p.get("name")).lower() for p in leer(RAIZ / "roster.json", []) if isinstance(p, dict)}
    cache = leer(CACHE, {})
    nuevas = 0
    nombres, artesanos, recetas = {}, [], {}

    for m in miembros[:300]:
        ch = m.get("character") or {}
        nombre, apellido = texto(ch.get("name"), 24), texto(ch.get("surname"), 24)
        slug = str(ch.get("slug") or "")
        if not nombre or not re.fullmatch(r"[\w\-%]+", slug, flags=re.UNICODE):
            continue
        completo = f"{nombre} {apellido}".strip()
        nombres[nombre.lower()] = completo
        clase = CLASES.get((ch.get("playable_class") or {}).get("id"), "")
        stp, prof = bz.get(f"/profile/wow/character/{urllib.parse.quote(slug)}/professions", NS_PERFIL)
        if stp != 200 or not prof:
            continue
        profesiones = []
        for grupo in ("primaries", "secondaries"):
            for pr in (prof.get(grupo) or [])[:4]:
                nombre_prof = texto((pr.get("profession") or {}).get("name"), 30)
                nombre_prof = PROF_ES.get(nombre_prof, nombre_prof)
                tiers = pr.get("tiers") or []
                nivel = max((t.get("skill_points") or 0 for t in tiers), default=0)
                maximo = max((t.get("max_skill_points") or 0 for t in tiers), default=0)
                if not nombre_prof:
                    continue
                profesiones.append({"nombre": nombre_prof, "nivel": int(nivel), "max": int(maximo)})
                for t in tiers:
                    for r in (t.get("known_recipes") or [])[:600]:
                        rid = r.get("id")
                        if not isinstance(rid, int):
                            continue
                        clave = str(rid)
                        if clave not in cache and nuevas < MAX_RECETAS_NUEVAS:
                            nuevas += 1
                            calidad = None
                            sr, rec = bz.get(f"/data/wow/recipe/{rid}", NS_ESTATICO)
                            item = ((rec or {}).get("crafted_item") or (rec or {}).get("alliance_crafted_item") or {})
                            if item.get("id"):
                                si, obj = bz.get(f"/data/wow/item/{item['id']}", NS_ESTATICO)
                                calidad = ((obj or {}).get("quality") or {}).get("type")
                            if sr == 200:
                                cache[clave] = {"calidad": CALIDAD.get(calidad, "common"), "objeto": bool(item.get("id"))}
                        receta = recetas.setdefault(clave, {"nombre": texto(r.get("name"), 80), "profesion": nombre_prof,
                                                           "calidad": (cache.get(clave) or {}).get("calidad", "common"),
                                                           "personajes": []})
                        if completo not in receta["personajes"]:
                            receta["personajes"].append(completo)
        if profesiones:
            artesanos.append({"personaje": completo, "clase": clase, "raider": nombre.lower() in raiders,
                              "profesiones": profesiones})

    artesanos.sort(key=lambda a: a["personaje"].lower())
    lista_recetas = sorted(recetas.values(), key=lambda r: (r["profesion"], r["nombre"]))
    for r in lista_recetas:
        r["personajes"].sort(key=str.lower)

    CACHE.parent.mkdir(exist_ok=True)
    escribir_si_cambia(CACHE, dict(sorted(cache.items(), key=lambda x: int(x[0]))))
    cambios = []
    if escribir_si_cambia(RAIZ / "nombres.json", dict(sorted(nombres.items()))):
        cambios.append("nombres.json")
    prof_json = {"actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "artesanos": artesanos, "recetas": lista_recetas}
    if escribir_si_cambia(RAIZ / "profesiones.json", prof_json, ["artesanos", "recetas"]):
        cambios.append("profesiones.json")
    print(f"Blizzard: {len(miembros)} miembros, {len(artesanos)} con profesiones, {len(lista_recetas)} recetas "
          f"({nuevas} calidades nuevas consultadas). Cambios: {', '.join(cambios) or 'ninguno'}")


if __name__ == "__main__":
    main()
