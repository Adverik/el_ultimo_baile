#!/usr/bin/env python3
"""Publica en un canal de Discord (webhook) los cambios de la web.

Uso:
  avisar_discord.py datos <carpeta_antes>   compara roster/actividad guardados antes del robot con los actuales
  avisar_discord.py reclutamiento <fichero_antes>   compara reclutamiento.json anterior con el actual
  avisar_discord.py prueba                  manda un mensaje de prueba

- La URL del webhook llega por DISCORD_WEBHOOK_URL (GitHub Secret). Si no está, no hace nada.
- Los nombres vienen de fuera (wowaudit): se envían con allowed_mentions vacío, así que
  nadie puede colar un @everyone ni mencionar a nadie, y se escapa el formato de Discord.
- Si Discord falla, avisa en el log pero no rompe el robot.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = "https://lastdance.cp-0.es"
MAX_LISTA = 10
CLASES = {"druid": "Druida", "paladin": "Paladín", "shaman": "Chamán", "priest": "Sacerdote",
          "warrior": "Guerrero", "hunter": "Cazador", "mage": "Mago", "warlock": "Brujo",
          "rogue": "Pícaro", "monk": "Monje", "deathknight": "Caballero de la Muerte"}
ROLES = {"tank": "Tank", "heal": "Healer", "healer": "Healer", "melee": "Melee", "ranged": "Ranged"}


def leer(ruta):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def limpio(texto, largo=60):
    """Texto plano seguro para Discord: sin saltos, sin formato markdown, recortado."""
    t = re.sub(r"\s+", " ", str(texto or "")).strip()[:largo]
    return re.sub(r"([\\*_~`|>#\[\]@<])", r"\\\1", t)


def lista(items):
    items = list(items)
    extra = len(items) - MAX_LISTA
    texto = ", ".join(items[:MAX_LISTA])
    return texto + (f" y {extra} más" if extra > 0 else "")


def enviar(lineas):
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not lineas:
        print("Avisos: nada que contar")
        return
    if not url:
        print("Avisos: el secreto DISCORD_WEBHOOK_URL está vacío o no existe, no se envía nada")
        return
    if not re.match(r"^https://(ptb\.|canary\.)?discord(app)?\.com/api/webhooks/\d+/[\w-]+$", url):
        host = re.sub(r"^(https?://[^/]+).*$", r"\1", url)[:40]  # solo el dominio, nunca el token
        print(f"Avisos: DISCORD_WEBHOOK_URL no parece un webhook de Discord (empieza por {host}), no se envía nada")
        return
    contenido = "\n".join(lineas)[:1900] + f"\n<{WEB}>"
    cuerpo = json.dumps({"content": contenido, "allowed_mentions": {"parse": []}}).encode()
    peticion = urllib.request.Request(url, data=cuerpo, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "ElUltimoBaile-web (https://lastdance.cp-0.es, 1.0)"})
    try:
        with urllib.request.urlopen(peticion, timeout=20) as r:
            print(f"Avisos: enviado ({r.status}), {len(lineas)} líneas")
    except urllib.error.HTTPError as e:
        print(f"AVISO: Discord respondió {e.code}", file=sys.stderr)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"AVISO: no se pudo enviar a Discord ({e.__class__.__name__})", file=sys.stderr)


def cambios_roster(antes, ahora):
    if not isinstance(antes, list) or not isinstance(ahora, list):
        return []
    def mapa(datos):
        return {str(p.get("name")): p for p in datos if isinstance(p, dict) and p.get("name")}
    a, b = mapa(antes), mapa(ahora)
    lineas = []
    altas = [n for n in b if n not in a]
    bajas = [n for n in a if n not in b]
    def desc(p):
        clase = CLASES.get(str(p.get("class", "")).lower().replace(" ", ""), "")
        rol = ROLES.get(str(p.get("role", "")).lower(), "")
        extra = " ".join(x for x in (clase, rol) if x)
        return f"**{limpio(p.get('name'))}**" + (f" ({extra})" if extra else "")
    if altas:
        lineas.append("🛡️ Nuevos raiders: " + lista(desc(b[n]) for n in sorted(altas)))
    if bajas:
        lineas.append("👋 Dejan el roster de raid: " + lista(f"**{limpio(n)}**" for n in sorted(bajas)))
    cambiados = [n for n in b if n in a and (a[n].get("role") != b[n].get("role") or a[n].get("class") != b[n].get("class"))]
    if cambiados:
        lineas.append("🔁 Cambian de rol: " + lista(desc(b[n]) for n in sorted(cambiados)))
    return lineas


def cambios_actividad(antes, ahora):
    if not isinstance(antes, dict) or not isinstance(ahora, dict):
        return []
    lineas = []
    pa, pb = antes.get("proxima_raid"), ahora.get("proxima_raid")
    if isinstance(pb, dict) and pb != pa and (not isinstance(pa, dict) or pa.get("fecha") != pb.get("fecha")):
        lineas.append(f"📅 Próxima raid: **{limpio(pb.get('fecha'), 10)}**, {limpio(pb.get('instancia') or pb.get('titulo'))}")
    def claves(lst, campos):
        return {tuple(str(x.get(c, "")) for c in campos) for x in (lst or []) if isinstance(x, dict)}
    nuevas = claves(ahora.get("ultimas_raids"), ("fecha", "instancia")) - claves(antes.get("ultimas_raids"), ("fecha", "instancia"))
    for fecha, inst in sorted(nuevas):
        lineas.append(f"⚔️ Raid registrada: {limpio(fecha, 10)}, {limpio(inst)}")
    botin_nuevo = claves(ahora.get("botin"), ("fecha", "personaje", "objeto")) - claves(antes.get("botin"), ("fecha", "personaje", "objeto"))
    if botin_nuevo:
        lineas.append("💰 Loot: " + lista(f"**{limpio(p)}** → {limpio(o)}" for _, p, o in sorted(botin_nuevo)))
    return lineas


def cambios_reclutamiento(antes, ahora):
    if not isinstance(antes, dict) or not isinstance(ahora, dict) or not antes.get("clases"):
        return []  # sin versión anterior (primera vez): no hay cambio que contar
    def estado(d):
        res = {}
        for c in d.get("clases", []):
            if not isinstance(c, dict):
                continue
            cerradas = set(c.get("cerradas") or [])
            for sp in c.get("specs") or []:
                res[(c.get("clase"), sp)] = sp not in cerradas
        return res
    a, b = estado(antes), estado(ahora)
    abiertas = [k for k, v in b.items() if v and a.get(k) is False or (v and k not in a)]
    cerradas = [k for k, v in b.items() if not v and a.get(k, True)]
    def agrupar(claves):
        por_clase = {}
        for clase, sp in claves:
            por_clase.setdefault(clase, []).append(sp)
        return "; ".join(f"**{CLASES.get(c, limpio(c))}** ({', '.join(limpio(s) for s in sps)})" for c, sps in por_clase.items())
    lineas = []
    if abiertas:
        lineas.append("🟢 Reclutamiento abierto: " + agrupar(abiertas))
    if cerradas:
        lineas.append("🔴 Reclutamiento cerrado: " + agrupar(cerradas))
    return lineas


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo == "prueba":
        enviar(["✅ Prueba de avisos de la web de **El Último Baile**. Si lees esto, el robot puede escribir aquí."])
    elif modo == "datos" and len(sys.argv) > 2:
        antes = Path(sys.argv[2])
        enviar(cambios_roster(leer(antes / "roster.json"), leer(RAIZ / "roster.json"))
               + cambios_actividad(leer(antes / "actividad.json"), leer(RAIZ / "actividad.json")))
    elif modo == "reclutamiento" and len(sys.argv) > 2:
        enviar(cambios_reclutamiento(leer(sys.argv[2]), leer(RAIZ / "reclutamiento.json")))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
