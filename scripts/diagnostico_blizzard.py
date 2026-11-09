#!/usr/bin/env python3
"""Diagnóstico de la API de Blizzard para WoW Forever: SOLO estructura, nunca valores personales.

1. Pide un token (client credentials) con BLIZZARD_CLIENT_ID / BLIZZARD_CLIENT_SECRET.
2. Prueba qué "namespace" usa Forever (no está documentado aún).
3. Con un personaje del roster (de wowaudit), mira qué campos da el perfil y las profesiones.
Solo imprime códigos HTTP, nombres de campos, tipos y recuentos.
"""
import base64, json, os, sys, urllib.error, urllib.parse, urllib.request

CID = os.environ.get("BLIZZARD_CLIENT_ID", "").strip()
SEC = os.environ.get("BLIZZARD_CLIENT_SECRET", "").strip()
WA = os.environ.get("WOWAUDIT_API_KEY", "").strip()
API = "https://eu.api.blizzard.com"


def http(url, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read(5 * 1024 * 1024))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, None


def forma(d, s=1, maxp=3):
    p = "  " * s
    if s > maxp:
        return
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, dict):
                print(f"{p}{k}: objeto"); forma(v, s + 1, maxp)
            elif isinstance(v, list):
                print(f"{p}{k}: lista[{len(v)}]")
                if v: forma(v[0], s + 1, maxp)
            else:
                extra = " (con espacios)" if isinstance(v, str) and " " in v.strip() else ""
                print(f"{p}{k}: {type(v).__name__}{extra}")


def main():
    if not CID or not SEC:
        sys.exit("Faltan BLIZZARD_CLIENT_ID / BLIZZARD_CLIENT_SECRET")
    auth = base64.b64encode(f"{CID}:{SEC}".encode()).decode()
    st, tok = http("https://oauth.battle.net/token", {"Authorization": f"Basic {auth}",
                   "Content-Type": "application/x-www-form-urlencoded"}, b"grant_type=client_credentials")
    print(f"Token: HTTP {st}")
    if not tok or "access_token" not in tok:
        sys.exit("No se pudo obtener el token (revisa los secretos)")
    H = {"Authorization": f"Bearer {tok['access_token']}", "Accept": "application/json"}

    # Un personaje del roster de wowaudit (nombre y reino solo se usan para la petición, no se imprimen)
    req = urllib.request.Request("https://api.wowaudit.com/v1/characters",
                                 headers={"Authorization": f"Bearer {WA}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        chars = json.loads(r.read())
    print(f"Personajes en wowaudit: {len(chars)}")

    # Namespaces candidatos para Forever
    sufijos = ["forever", "classicforever", "classic1x", "classicann", "classic", "classicsod", ""]
    buenos = []
    print("\n===== Reinos por namespace (dynamic-*)")
    for suf in sufijos:
        ns = f"dynamic-{suf}-eu" if suf else "dynamic-eu"
        st, d = http(f"{API}/data/wow/realm/index?namespace={ns}&locale=es_ES", H)
        n = len((d or {}).get("realms", []))
        nombres = {str(x.get("name", "")).lower() for x in (d or {}).get("realms", [])}
        reinos = {str(c.get("realm", "")).lower() for c in chars}
        coinciden = len(reinos & nombres)
        print(f"  {ns}: HTTP {st}, {n} reinos, reinos del roster encontrados: {coinciden}/{len(reinos)}")
        if coinciden:
            buenos.append((suf, d))

    forever(H, chars)
    return
    print("\n===== Perfil de personajes por namespace (profile-*)")
    for suf in sufijos:
        ns = f"profile-{suf}-eu" if suf else "profile-eu"
        ok = 0; ejemplo = None; prof = None
        for c in chars[:13]:
            slug = None
            for s2, d in buenos:
                for x in d.get("realms", []):
                    if str(x.get("name", "")).lower() == str(c.get("realm", "")).lower():
                        slug = x.get("slug"); break
                if slug: break
            slug = slug or str(c.get("realm", "")).lower().replace(" ", "-").replace("'", "")
            nombre = urllib.parse.quote(str(c.get("name", "")).lower())
            st, d = http(f"{API}/profile/wow/character/{slug}/{nombre}?namespace={ns}&locale=es_ES", H)
            if st == 200:
                ok += 1
                ejemplo = ejemplo or d
                if prof is None:
                    sp, prof = http(f"{API}/profile/wow/character/{slug}/{nombre}/professions?namespace={ns}&locale=es_ES", H)
                    prof = prof if sp == 200 else {"_http": sp}
        print(f"  {ns}: {ok}/{min(13, len(chars))} perfiles encontrados")
        if ejemplo:
            print("    campos del perfil:"); forma(ejemplo, 3, 4)
            print("    profesiones:"); forma(prof, 3, 5)
            break


def forever(H, chars):
    """Prueba el acceso de Forever con el roster de la hermandad (nombres de reinos y gremio: públicos)."""
    print("\n===== Forever: reinos y roster de la hermandad")
    reinos_wa = sorted({str(c.get("realm", "")) for c in chars})
    print(f"  reino en wowaudit: {reinos_wa}")
    slugs = set()
    for ns in ("dynamic-forever-eu", "profile-forever-eu"):
        st, d = http(f"{API}/data/wow/realm/index?namespace={ns}&locale=es_ES", H)
        rs = (d or {}).get("realms", [])
        print(f"  realm index {ns}: HTTP {st}, {len(rs)} reinos")
        for x in rs[:40]:
            print(f"    - {x.get('name')} -> {x.get('slug')}")
            slugs.add(x.get("slug"))
    for r in reinos_wa:
        base = r.lower().split("(")[0].strip()
        slugs |= {base.replace(" ", "-"), "normal", "pve", "eu-normal", "forever"}
    gremios = ["el-%C3%BAltimo-baile", "el-ultimo-baile"]
    for slug in sorted(s for s in slugs if s):
        for g in gremios:
            for ns in ("profile-forever-eu",):
                st, d = http(f"{API}/data/wow/guild/{slug}/{g}/roster?namespace={ns}&locale=es_ES", H)
                if st == 200 or slug in ("normal",):
                    print(f"  roster {slug}/{g} ({ns}): HTTP {st}")
                if st == 200:
                    miembros = (d or {}).get("members", [])
                    nombres = [str(m.get("character", {}).get("name", "")) for m in miembros]
                    print(f"    miembros: {len(miembros)}; nombres con espacio: {sum(' ' in n for n in nombres)}; con guion: {sum('-' in n for n in nombres)}")
                    print("    forma de un miembro:"); forma(miembros[0] if miembros else {}, 3, 5)
                    if miembros:
                        ch = miembros[0].get("character", {})
                        rs = (ch.get("realm") or {}).get("slug", slug)
                        nm = urllib.parse.quote(str(ch.get("name", "")).lower().replace(" ", "-"))
                        sp, perfil = http(f"{API}/profile/wow/character/{rs}/{nm}?namespace={ns}&locale=es_ES", H)
                        print(f"    perfil del primero: HTTP {sp}")
                        if perfil: forma(perfil, 3, 4)
                        sp, prof = http(f"{API}/profile/wow/character/{rs}/{nm}/professions?namespace={ns}&locale=es_ES", H)
                        print(f"    profesiones del primero: HTTP {sp}")
                        if prof: forma(prof, 3, 5)
                    return


if __name__ == "__main__":
    main()
