#!/usr/bin/env python3
"""Baja los últimos sorteos de Florida Pick 3/Pick 4 y actualiza results.json.
Solo biblioteca estándar. Si algo falla NO borra ni cambia results.json."""
import html, json, re, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://lotteryguru.com/united-states-lottery-results/"
URL_P3 = BASE + "us-pick-3-fl/us-pick-3-fl-results-history"
URL_P4 = BASE + "us-pick-4-fl/us-pick-4-fl-results-history"
OUT = "results.json"
MAX_GUARDAR = 120
MESES = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


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


def parse(h, cifras_ok):
    """Devuelve {(fecha, 'MID'|'EVE'): [dígitos]} leyendo el texto de la página."""
    t = tokens(h)
    out, fecha, ses, dig, skip = {}, None, None, None, 0
    hoy = datetime.now(timezone.utc).date()
    for i, tok in enumerate(t):
        if skip:
            skip -= 1
            continue
        if (i + 2 < len(t) and tok.isdigit() and len(tok) <= 2
                and t[i + 1][:3].title() in MESES and re.fullmatch(r"\d{4}", t[i + 2])):
            try:
                f = datetime(int(t[i + 2]), MESES[t[i + 1][:3].title()], int(tok)).date()
            except ValueError:
                f = None
            if f and f <= hoy + timedelta(days=1):
                fecha, ses, dig, skip = f.isoformat(), None, None, 2
                continue
        if fecha and tok in ("Midday", "Evening"):
            ses, dig = ("MID" if tok == "Midday" else "EVE"), []
        elif tok == "Jackpot":
            if fecha and ses and dig and len(dig) in cifras_ok:
                out[(fecha, ses)] = dig
            ses = dig = None
        elif dig is not None and re.fullmatch(r"\d", tok):
            dig.append(tok)
    return out


def main():
    p3 = parse(bajar(URL_P3), (4,))      # 3 cifras + bola de fuego
    p4 = parse(bajar(URL_P4), (5,))      # 4 cifras + bola de fuego
    if not p3:
        print("ERROR: no se leyó ningún sorteo de Pick 3 (¿cambió la página?)")
        return 1

    nuevos = {}
    for k, d in p3.items():
        fb3 = d[3]
        x = {"d": k[0], "s": k[1], "p3": "".join(d[:3]), "p4": ""}
        if k in p4:
            if p4[k][4] == fb3:
                x["p4"] = "".join(p4[k][:4])
            else:
                print(f"AVISO {k}: bola de fuego distinta entre Pick 3 y Pick 4; "
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

    orden = sorted(actual.values(), key=lambda x: (x["d"], 0 if x["s"] == "MID" else 1))
    orden = orden[-MAX_GUARDAR:]
    data = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "draws": orden}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    ult = orden[-1]
    print(f"Actualizado. Último: {ult['d']} {ult['s']} {ult['p3']} {ult['p4']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
