#!/usr/bin/env python3
"""Actualiza discord.json con el recuento público del servidor de Discord de la hermandad.

- Usa el enlace de invitación público (sin bot ni clave): GET /invites/<código>?with_counts=true.
- Minimización de datos: solo pasan el nombre del servidor y dos números (miembros y conectados).
  Nunca nombres de usuarios.
- Lo hace el robot de GitHub, no el navegador del visitante: la web no carga nada de Discord.
- Si algo falla, no toca discord.json y no rompe el resto del robot (sale con 0 y avisa).
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

INVITACION = "yc89W4YpF"
URL = f"https://discord.com/api/v10/invites/{INVITACION}?with_counts=true"
DESTINO = Path(__file__).resolve().parent.parent / "discord.json"
TIMEOUT_SEGUNDOS = 20
MAX_BYTES = 256 * 1024


def aviso(mensaje: str) -> None:
    print(f"AVISO: {mensaje}", file=sys.stderr)
    sys.exit(0)


def entero(valor):
    return valor if isinstance(valor, int) and 0 <= valor < 10_000_000 else None


def main() -> None:
    peticion = urllib.request.Request(URL, headers={
        "Accept": "application/json",
        "User-Agent": "ElUltimoBaile-web (https://lastdance.cp-0.es, 1.0)",
    })
    try:
        with urllib.request.urlopen(peticion, timeout=TIMEOUT_SEGUNDOS) as r:
            cuerpo = r.read(MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as e:
        aviso(f"no se pudo consultar Discord ({e})")
    if len(cuerpo) > MAX_BYTES:
        aviso("respuesta demasiado grande")
    try:
        datos = json.loads(cuerpo)
    except ValueError:
        aviso("respuesta no es JSON")

    guild = datos.get("guild") or {}
    miembros = entero(datos.get("approximate_member_count"))
    conectados = entero(datos.get("approximate_presence_count"))
    if miembros is None:
        aviso("la respuesta no trae el recuento (¿invitación caducada?)")

    nuevo = {
        "servidor": str(guild.get("name", ""))[:60],
        "miembros": miembros,
        "conectados": conectados,
    }
    anterior = {}
    if DESTINO.exists():
        try:
            anterior = json.loads(DESTINO.read_text(encoding="utf-8"))
        except ValueError:
            anterior = {}
    if {k: anterior.get(k) for k in nuevo} == nuevo:
        print("Discord: sin cambios")
        return
    nuevo["actualizado"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    DESTINO.write_text(json.dumps(nuevo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Discord: {miembros} miembros, {conectados} conectados")


if __name__ == "__main__":
    main()
