# -*- coding: utf-8 -*-
"""Recupere les pages sources et signale ce qui a bouge.

C'est le seul endroit du depot qui touche au reseau. Deux sources :

  game8    fiches "<Nom> Location, Evolutions, and Stats" -> raw/<Nom>.html
           Source historique, celle que parse.py sait lire.
  aniidex  base de donnees communautaire (aniidex.com) -> raw_aniidex/<slug>.html
           Elle couvre les Aniimo que Game8 n'a pas encore redigees (No. 084 et
           au-dela) et donne, en plus, le cout en EP, le temps de recharge et la
           Puissance de chaque competence.

Le fichier raw/_sources.json garde pour chaque page son URL, l'empreinte de son
contenu utile et la date de relevage : c'est ce qui permet de savoir, au passage
suivant, ce qui est nouveau, ce qui a change et ce qui a disparu.

    python fetch.py              constate sans rien telecharger
    python fetch.py --apply      telecharge ce qui manque ou a change
    python fetch.py --apply --source aniidex
    python fetch.py --apply --all   re-releve aussi les pages deja connues
"""
import io, os, re, sys, json, time, hashlib, urllib.request, urllib.error

UA = "Mozilla/5.0 (compatible; amo-tierlist/1.0; +https://github.com/Alex-mant/amo)"
DELAY = 1.0                      # une seconde entre deux pages, on ne se presse pas
INDEX = "raw/_sources.json"

G8_LIST = "https://game8.co/games/Aniimo/archives/618058"
G8_PAGE = "https://game8.co/games/Aniimo/archives/%s"
G8_TITLE = re.compile(r"<title>(.*?) Location, Evolutions, and Stats", re.S)
G8_LINK = re.compile(r"data-track-nier-value='([^']+)'\s+href='/games/Aniimo/archives/(\d+)'")

AX_LIST = "https://aniidex.com/aniimo/"
AX_PAGE = "https://aniidex.com/aniimo/%s/"
AX_LINK = re.compile(r'href="/aniimo/([a-z0-9-]+)/?"')


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def body_hash(html):
    """Empreinte du contenu utile. Game8 et Nuxt glissent dans chaque page des
    jetons, des compteurs et des horodatages qui changent a chaque appel : les
    prendre en compte ferait clignoter toutes les pages a chaque passage."""
    h = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", html, flags=re.S)
    h = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))
    return hashlib.sha256(h.encode("utf-8")).hexdigest()[:16]


def load_index():
    return json.load(io.open(INDEX, encoding="utf-8")) if os.path.exists(INDEX) else {}


def save_index(ix):
    io.open(INDEX, "w", encoding="utf-8", newline="\n").write(
        json.dumps(ix, ensure_ascii=False, indent=1, sort_keys=True))


# --------------------------------------------------------------------------
# Adaptateurs : chacun rend {chemin_local: url}
# --------------------------------------------------------------------------

def wanted_game8():
    """Le menu lateral de la liste porte le nom exact de chaque fiche. On ne
    garde que les libelles dont la page est bien une fiche d'Aniimo : le titre
    seul en decide, pas une liste de mots a exclure tenue a la main."""
    html = get(G8_LIST)
    out, ids = {}, {}
    for label, num in G8_LINK.findall(html):
        ids.setdefault(label.strip(), num)
    known = set()
    if os.path.exists("raw/parsed.json"):
        known = {r["name"] for r in json.load(io.open("raw/parsed.json", encoding="utf-8"))}
    for label, num in sorted(ids.items()):
        path = "raw/%s.html" % label.replace(" ", "_")
        # deja parsee -> c'est une fiche ; sinon on verifiera au telechargement
        if label in known or os.path.exists(path):
            out[path] = G8_PAGE % num
        else:
            out[path] = G8_PAGE % num
    return out, ids


def wanted_aniidex():
    html = get(AX_LIST)
    slugs = sorted(set(AX_LINK.findall(html)))
    return {"raw_aniidex/%s.html" % s: AX_PAGE % s for s in slugs}


def is_aniimo_page(path, html):
    if path.startswith("raw_aniidex/"):
        return "form-tile__label" in html or "Combat Skills" in html
    return bool(G8_TITLE.search(html))


# --------------------------------------------------------------------------

def run(sources, apply_, refetch):
    ix = load_index()
    plan, seen = [], set()

    for src in sources:
        if src == "game8":
            want, _ = wanted_game8()
        else:
            want = wanted_aniidex()
        print("%-8s %d pages annoncees par la source" % (src, len(want)))
        for path, url in sorted(want.items()):
            seen.add(path)
            if not os.path.exists(path):
                plan.append((src, path, url, "nouvelle"))
            elif refetch or path not in ix:
                plan.append((src, path, url, "a verifier"))

    gone = [p for p in ix if p not in seen and p.split("/")[0] in
            {"raw" if "game8" in sources else None, "raw_aniidex" if "aniidex" in sources else None}]
    for p in sorted(gone):
        print("  disparue de la source : %s" % p)

    print("%d page(s) a traiter%s" % (len(plan), "" if apply_ else " -- ajouter --apply pour telecharger"))
    if not apply_:
        for s, p, u, why in plan[:40]:
            print("  %-10s %-44s %s" % (why, p, u))
        return

    added = changed = same = skipped = 0
    for i, (src, path, url, why) in enumerate(plan, 1):
        try:
            html = get(url)
        except urllib.error.HTTPError as e:
            print("  [%d/%d] %-40s HTTP %s" % (i, len(plan), os.path.basename(path), e.code))
            time.sleep(DELAY)
            continue
        if not is_aniimo_page(path, html):
            skipped += 1
            time.sleep(DELAY)
            continue
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        new = body_hash(html)
        old = ix.get(path, {}).get("hash")
        if old is None:
            added += 1
        elif old != new:
            changed += 1
            print("  MODIFIEE : %s" % path)
        else:
            same += 1
        io.open(path, "w", encoding="utf-8", newline="\n").write(html)
        ix[path] = {"url": url, "source": src, "hash": new,
                    "vu_le": time.strftime("%Y-%m-%d")}
        if i % 25 == 0:
            save_index(ix)
            print("  ... %d/%d" % (i, len(plan)))
        time.sleep(DELAY)

    save_index(ix)
    print("nouvelles %d | modifiees %d | inchangees %d | ecartees (pas une fiche) %d"
          % (added, changed, same, skipped))


if __name__ == "__main__":
    a = sys.argv[1:]
    src = a[a.index("--source") + 1] if "--source" in a else "game8,aniidex"
    run([s for s in src.split(",") if s], "--apply" in a, "--all" in a)
