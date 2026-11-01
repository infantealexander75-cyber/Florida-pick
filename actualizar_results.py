#!/usr/bin/env python3
"""Baja los últimos sorteos de Florida Pick 3/Pick 4 de DOS fuentes y actualiza results.json.
Solo biblioteca estándar. Si algo falla NO borra ni cambia results.json."""
import html, json, re, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

# (nombre, url Pick 3, url Pick 4). La primera es la más rápida.
FUENTES = [
    ("lottery.net",
     "https://www.lottery.net/florida/pick-3/numbers",
     "https://www.lottery.net/florida/pick-4/numbers"),
    ("lotteryguru.com",
     "https://lotteryguru.com/united-states-lottery-results/us-pick-3-fl/us-pick-3-fl-results-history",
     "https://lotteryguru.com/united-states-lottery-results/us-pick-4-fl/us-pick-4-fl-results-history"),
]
OUT = "results.json"
MAX_GUARDAR = 120
MESES = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
RE_HORA = re.compile(r"^(\d{1,2}:\d{2}|AM|PM|ET)$", re.I)


def aviso(msg):
    print(f"::warning::{msg}")


def bajar(url):
    err = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa
            err = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"no pude bajar {url}: {err}")


def tokens(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    return html.unescape(h).split()


def fecha_en(t, i, hoy):
    """Reconoce '31 Oct 2026' o 'October 31, 2026' en la posición i. Devuelve (iso, tokens usados)."""
    a = t[i]
    try:
        if a.isdigit() and len(a) <= 2 and i + 2 < len(t) \
                and t[i + 1][:3].title() in MESES and re.fullmatch(r"\d{4}", t[i + 2]):
            f = datetime(int(t[i + 2]), MESES[t[i + 1][:3].title()], int(a)).date()
        elif a.isalpha() and len(a) >= 3 and a[:3].title() in MESES and i + 2 < len(t) \
                and re.fullmatch(r"\d{1,2},?", t[i + 1]) and re.fullmatch(r"\d{4}", t[i + 2]):
            f = datetime(int(t[i + 2]), MESES[a[:3].title()], int(t[i + 1].rstrip(","))).date()
        else:
            return None, 0
    except ValueError:
        return None, 0
    if f > hoy + timedelta(days=1):
        return None, 0
    return f.isoformat(), 3


def parse(h, cifras_ok):
    """{(fecha,'MID'|'EVE'): [dígitos]} leyendo el texto de la página."""
    t = tokens(h)
    out, fecha, ses, estado, dig = {}, None, None, None, []
    hoy = datetime.now(timezone.utc).date()
    i = 0
    while i < len(t):
        tok = t[i]
        if estado == "reunir":
            if re.fullmatch(r"\d", tok):
                dig.append(tok)
                i += 1
                continue
            if fecha and ses and len(dig) in cifras_ok:
                out[(fecha, ses)] = dig
            estado, dig = None, []          # y se vuelve a mirar este token
            continue
        if estado == "espera":
            if re.fullmatch(r"\d", tok):
                estado, dig = "reunir", [tok]
                i += 1
                continue
            if RE_HORA.match(tok):
                i += 1
                continue
            estado = None                    # sin números todavía: se ignora
            continue
        f, n = fecha_en(t, i, hoy)
        if f:
            fecha, ses, i = f, None, i + n
            continue
        if fecha and tok in ("Midday", "Evening"):
            ses, estado, dig = ("MID" if tok == "Midday" else "EVE"), "espera", []
        i += 1
    if estado == "reunir" and fecha and ses and len(dig) in cifras_ok:
        out[(fecha, ses)] = dig
    return out


def juntar(lecturas, etiqueta):
    """Une lo leído por varias fuentes. Si dos fuentes discrepan en un sorteo, se omite ese."""
    res, malos = {}, set()
    for nombre, d in lecturas:
        for k, v in d.items():
            if k in malos:
                continue
            if k in res and res[k] != v:
                aviso(f"{etiqueta} {k[0]} {k[1]}: las fuentes no coinciden "
                      f"({''.join(res[k])} vs {''.join(v)} en {nombre}); se omite")
                malos.add(k)
                del res[k]
            else:
                res[k] = v
    return res


def leer(idx, cifras):
    lect = []
    for f in FUENTES:
        try:
            lect.append((f[0], parse(bajar(f[idx]), cifras)))
            print(f"{f[0]} {'Pick 3' if idx == 1 else 'Pick 4'}: {len(lect[-1][1])} sorteos")
        except Exception as e:  # noqa
            aviso(f"{f[0]}: {e}")
    return lect


def main():
    l3, l4 = leer(1, (4,)), leer(2, (5,))     # 3 o 4 cifras + bola de fuego
    p3, p4 = juntar(l3, "Pick 3"), juntar(l4, "Pick 4")
    if not p3:
        print("ERROR: no se leyó ningún sorteo de Pick 3 (¿cambiaron las páginas?)")
        return 1

    nuevos = {}
    for k, d in p3.items():
        x = {"d": k[0], "s": k[1], "p3": "".join(d[:3]), "p4": ""}
        if k in p4:
            if p4[k][4] == d[3]:
                x["p4"] = "".join(p4[k][:4])
            else:
                aviso(f"{k[0]} {k[1]}: bola de fuego distinta entre Pick 3 y Pick 4; "
                      "se guarda solo el Pick 3 por ahora")
        nuevos[k] = x

    try:
        with open(OUT, encoding="utf-8") as f:
            viejo = json.load(f)
        actual = {(x["d"], x["s"]): x for x in viejo.get("draws", [])}
    except Exception:
        actual = {}

    cambio = False
    for k, x in nuevos.items():
        a = actual.get(k)
        if a is None:
            actual[k] = x
            cambio = True
        else:
            merged = dict(x)
            if not merged["p4"] and a.get("p4"):
                merged["p4"] = a["p4"]
            if merged != {kk: a.get(kk, "") for kk in ("d", "s", "p3", "p4")}:
                actual[k] = merged
                cambio = True

    if not cambio:
        print(f"Sin cambios ({len(nuevos)} sorteos leídos).")
        return 0

    orden = sorted(actual.values(), key=lambda x: (x["d"], 0 if x["s"] == "MID" else 1))[-MAX_GUARDAR:]
    data = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "draws": orden}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    u = orden[-1]
    print(f"Actualizado. Último: {u['d']} {u['s']} {u['p3']} {u['p4']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
