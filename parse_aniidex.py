# -*- coding: utf-8 -*-
"""Lit les fiches aniidex.com de raw_aniidex/ -> raw/parsed_aniidex.json

Meme schema que parse.py, pour que score.py n'ait pas a savoir d'ou vient une
fiche. Trois differences, gardees telles quelles :

  - les competences portent en plus leur Puissance, leur cout en EP, leur temps
    de recharge (champs mi / ep / cd) et leurs etiquettes (pills : type de degat,
    statistique sur laquelle elles montent, element, Controle, Statut anormal...).
    Game8 ne publie rien de tout cela, et ce sont ces chiffres qui permettront de
    calculer un kit au lieu de le noter a la main ;
  - le champ upgrades porte la version amelioree d'une competence (l'eveil) ;
  - le champ src vaut "aniidex", pour que la provenance de chaque ligne reste
    lisible dans data.js ;
  - les formes regionales ne sont pas des pages separees. La fiche porte la
    liste de ses formes ; leurs stats et leurs competences sont celles de la
    base, seuls les elements changent. On ne cree donc une entree de forme que
    si la fiche la nomme, et on ne lui invente rien de plus.
"""
import io, os, re, json, glob

ELEMENTS = ["Fire", "Water", "Grass", "Wind", "Earth", "Ice", "Lightning", "Dark", "Light"]
ROLES = ["DPS", "Break", "Support", "Regen", "Heal"]
STAGES = ["Lumin", "Gamma", "Nova"]
STATKEY = {"HP": "hp", "ATK": "atk", "P.DEF": "pdef", "REGEN": "reg",
           "M.DEF": "mdef", "BREAK": "brk"}
# Les icones du site portent le nom interne du jeu, pas celui affiche dans le
# jeu : Rock est l'element que la fiche appelle Earth, Electric celui qu'elle
# appelle Lightning, Holy celui qu'elle appelle Light. Sans cette table, les
# elements des formes regionales sortiraient sous des noms que le reste du
# depot ne connait pas.
ICONEL = {"Rock": "Earth", "Electric": "Lightning", "Holy": "Light"}

TAG = re.compile(r"<[^>]+>")
SECT = re.compile(r'<h3 class="section-heading"[^>]*>(.*?)</h3>')
CARD = re.compile(r'<article([^>]*)class="([^"]*ab-card[^"]*)"[^>]*>(.*?)</article>', re.S)
H4 = re.compile(r"<h4>(.*?)</h4>", re.S)
PILL = re.compile(r'<span class="[^"]*ab-pill[^"]*"[^>]*>(?:<[^>]+>)*([^<]+)</span>')
CHIP = re.compile(r'<span class="ab-chip"><span>(.*?)</span><b>(.*?)</b></span>')
DETAILS = re.compile(r'<div class="ab-card__details">.*?<p>(.*?)</p>', re.S)
TILE = re.compile(r'<button[^>]*class="[^"]*form-tile[^"]*"[^>]*>(.*?)</button>', re.S)
LABEL = re.compile(r'class="form-tile__label"[^>]*>(.*?)</span>', re.S)
ICON = re.compile(r"IconAttribute/(\w+)\.webp")
# Le jeu designe sur chaque fiche DEUX statistiques recommandees -- le pouce vert
# de l'hexagone. Ce ne sont pas les deux stats du role : c'est par Aniimo, et
# c'est ce que le jeu lui-meme couronne (potentiel plafonne a 24 au lieu de 20,
# et c'est a elles que le Capafruit ajoute son point). aniidex les ecrit de deux
# facons selon la fiche, d'ou les deux lectures ; 43 fiches sur 100 ne les
# portent pas du tout, et on ne les devine pas.
RECO = re.compile(r"Recommended stat: (HP|ATK|P\.DEF|REGEN|M\.DEF|BREAK)")
RECOALT = re.compile(r'alt="([^"]*\(recommended\)[^"]*)"')


def text(s):
    s = TAG.sub(" ", s)
    s = (s.replace("&#39;", "'").replace("&amp;", "&").replace("&quot;", '"')
          .replace("&nbsp;", " ").replace("&#160;", " ").replace("&rsquo;", "'")
          .replace("’", "'"))
    return re.sub(r"\s+", " ", s).strip()


def sections(html):
    """{titre de section: portion de HTML}, dans l'ordre de la page."""
    marks = [(m.start(), text(m.group(1))) for m in SECT.finditer(html)]
    out = {}
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(html)
        out[name] = html[pos:end]
    return out


def cards(block, upgraded=False):
    """Les cartes marquees ab-card--upgraded sont la version amelioree d'une
    competence deja listee (l'eveil du jeu), pas une competence de plus : elles
    sortent a part, sinon la competence compte double."""
    out = []
    for _, cls, c in CARD.findall(block or ""):
        if ("ab-card--upgraded" in cls) != upgraded:
            continue
        nm = H4.search(c)
        if not nm:
            continue
        d = DETAILS.search(c)
        chips = {text(a): text(b) for a, b in CHIP.findall(c)}
        e = {"n": text(nm.group(1)), "d": text(d.group(1)) if d else "",
             "pills": [text(p) for p in PILL.findall(c)]}
        for lbl, key in [("Might", "mi"), ("EP cost", "ep"), ("Ultimate cost", "ep"),
                         ("Cooldown", "cd")]:
            if lbl in chips:
                e[key] = chips[lbl]
        out.append(e)
    return out


def parse(path):
    html = io.open(path, encoding="utf-8", errors="replace").read()
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S)

    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    if not h1:
        return None
    name = re.sub(r"\s+Aniimo$", "", text(h1.group(1)))

    head = text(html[max(0, h1.start() - 1200):h1.end() + 2500])
    no = re.search(r"#\s*(\d+)\s*" + re.escape(name), head)
    stage = next((s for s in STAGES if re.search(r"\b%s\b" % s, head)), None)
    role = next((r for r in ROLES if re.search(r"\b%s\b" % r, head)), None)
    els = [e for e in ELEMENTS if re.search(r"\b%s\b" % e, head)]

    names = [text(x) for x in re.findall(r'class="[^"]*stat-hex__name[^"]*"[^>]*>(.*?)<', html)]
    vals = [text(x) for x in re.findall(r'class="[^"]*stat-hex__value[^"]*"[^>]*>(.*?)<', html)]
    if len(names) != 6 or len(vals) != 6:
        return None
    stats = {}
    for a, b in zip(names, vals):
        if a not in STATKEY or not b.isdigit():
            return None
        stats[STATKEY[a]] = int(b)

    S = sections(html)
    traits = cards(S.get("Traits & Passives"))
    atk = cards(S.get("Basic Attacks"))
    ult = cards(S.get("Ultimate"))
    skills = cards(S.get("Combat Skills"))
    upgrades = cards(S.get("Combat Skills"), upgraded=True)

    # Le marqueur "(Ultimate)" devant l'ultime et la signature "(Phys., Melee,
    # Earth)" de l'attaque de base sont la forme que Game8 leur donne ; on la
    # reproduit pour que les deux sources se comparent ligne a ligne.
    innate = []
    for u in ult:
        innate.append({"n": u["n"], "d": "(Ultimate) " + u["d"],
                       **{k: u[k] for k in ("mi", "ep", "cd") if k in u}})
    for a in atk:
        innate.append({"n": a["n"], "d": a["d"],
                       **{k: a[k] for k in ("mi", "ep", "cd") if k in a}})

    # "Hauling" chez aniidex, "Carry" chez Game8 : meme capacite, deux libelles.
    hl = []
    for _, _cls, c in CARD.findall(S.get("Homeland Abilities") or ""):
        nm, lv = H4.search(c), re.search(r"Lv\s*(\d+)", text(c))
        if nm and lv:
            a = text(nm.group(1))
            hl.append(["Carry" if a == "Hauling" else a, int(lv.group(1))])

    mob = cards(S.get("Mobility"))
    desc = re.search(r"Description\s+(.*?)\s+(?:Home Food|Recommended Items)", text(html))

    # Les formes regionales n'ont pas de page a elles : la fiche de base porte
    # une tuile par forme, et cette tuile est le seul endroit ou le site dit
    # quels elements la forme remplace. On ne releve que cela.
    reco = sorted({STATKEY[x] for x in RECO.findall(html)})
    if not reco:
        a = RECOALT.search(html)
        if a:
            reco = sorted({STATKEY[c.split()[0].upper()]
                           for c in a.group(1).split(",")
                           if "(recommended)" in c and c.split()[0].upper() in STATKEY})

    forms = []
    for b in TILE.findall(html):
        lab = LABEL.search(b)
        if lab:
            lab = text(lab.group(1))
            if lab and lab.lower() not in ("basic", "basic form"):
                forms.append([lab, [ICONEL.get(e, e) for e in ICON.findall(b)]])

    return {
        "name": name, "no": no.group(1) if no else None,
        "kind": "base", "src": "aniidex",
        "el": els, "role": role, "stage": stage,
        "stats": stats, "total": sum(stats.values()), "reco": reco,
        "homeland": hl,
        "pathfinding": None,
        "mobility": mob[0]["n"] if mob else None,
        "traits": traits,
        "skills": skills,
        "innate": innate,
        "upgrades": upgrades,
        "log": desc.group(1) if desc else None,
        "forms": forms,
    }


if __name__ == "__main__":
    out, bad = [], []
    for p in sorted(glob.glob("raw_aniidex/*.html")):
        r = parse(p)
        (out if r else bad).append(r or os.path.basename(p))
    io.open("raw/parsed_aniidex.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("aniidex : %d fiches lues, %d ecartees %s" % (len(out), len(bad), bad[:6]))
    miss = [r["name"] for r in out if not r["role"] or not r["el"] or not r["skills"]]
    print("role / element / competences manquants (%d) : %s" % (len(miss), ", ".join(miss[:10])))
    rc = [r for r in out if r["reco"]]
    print("stats recommandees par le jeu : %d fiches sur %d" % (len(rc), len(out)))
