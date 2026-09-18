# -*- coding: utf-8 -*-
"""
Construit la tier list Aniimo a partir des donnees brutes (raw/parsed.json).

Modele : on suppose chaque Aniimo pousse au MAXIMUM de ce que le jeu permet.
Le plafond d'investissement est identique pour tous (meme niveau max, memes
paliers de Resonance, meme cap de potentiel), donc ce qui differencie deux
Aniimo a investissement egal est :
  1. leurs stats de base                          -> STAT
  2. les stats qu'ils peuvent couronner a 24      -> STAT (bonus potentiel)
  3. la puissance chiffree de leur kit            -> KIT
  4. ce que leur kit apporte a une equipe         -> SYNERGIE

Le KIT ne vient plus d'expressions regulieres : les 116 kits distincts ont ete
lus un par un et notes sur 6 axes (voir RUBRIC.md et kits.json). Les 91 formes
regionales qui reutilisent le kit de leur base heritent de ses notes via
raw/_kitmap.json.

Sortie : data.js
"""
import json, io, collections

D = json.load(io.open("raw/parsed.json", encoding="utf-8"))
KITS = json.load(io.open("kits.json", encoding="utf-8"))
KMAP = json.load(io.open("raw/_kitmap.json", encoding="utf-8"))
SYN = json.load(io.open("synergy.json", encoding="utf-8"))
try:
    REF = json.load(io.open("raw/_tier_game8.json", encoding="utf-8"))
except Exception:
    REF = {}
REFTIER = {n: t for t, names in REF.items() for n in names}

STATS = ["hp", "atk", "pdef", "mdef", "brk", "reg"]
AXES = ["dmg", "team", "brk", "sust", "res", "ctrl"]

# ---------------------------------------------------------------- 1. STAT ---
# Poids par role : ce que la stat apporte reellement a ce role.
W = {
    "DPS":     {"atk": .50, "brk": .15, "hp": .15, "pdef": .07, "mdef": .07, "reg": .06},
    "Break":   {"brk": .45, "atk": .18, "hp": .17, "pdef": .08, "mdef": .07, "reg": .05},
    "Support": {"reg": .35, "hp": .22, "mdef": .16, "pdef": .12, "atk": .10, "brk": .05},
    "Regen":   {"reg": .45, "hp": .22, "mdef": .13, "pdef": .11, "atk": .05, "brk": .04},
    "Heal":    {"reg": .38, "hp": .25, "mdef": .17, "pdef": .12, "atk": .05, "brk": .03},
}
# Stats "favorables" (pouce vert) : potentiel plafonne a 24 au lieu de 20.
# A investissement maximal, elles disposent donc de +20% de marge de croissance.
FAV = {
    "DPS":     ["atk", "hp"],
    "Break":   ["brk", "hp"],
    "Support": ["reg", "mdef"],
    "Regen":   ["reg", "hp"],
    "Heal":    ["reg", "hp"],
}
CROWN = 24.0 / 20.0

# Bornes de normalisation calculees sur TOUT le roster jouable (207 entrees).
PLAY = [r for r in D if r["kind"] in ("base", "form", "prismana")]
LO = {s: min(r["stats"][s] for r in PLAY) for s in STATS}
HI = {s: max(r["stats"][s] for r in PLAY) for s in STATS}


def stat_score(r):
    """0..100. Stats de base normalisees, ponderees par role, majorees du
    potentiel couronnable a 24 sur les stats favorables du role."""
    role = r["role"] or "DPS"
    w, fav = W[role], FAV[role]
    tot = det = 0.0
    parts = {}
    for s in STATS:
        n = (r["stats"][s] - LO[s]) / max(1, HI[s] - LO[s])
        eff = n * (CROWN if s in fav else 1.0)
        parts[s] = round(eff * 100, 1)
        tot += w[s] * eff
        det += w[s] * (CROWN if s in fav else 1.0)
    return min(100.0, tot / det * 100), parts


# ----------------------------------------------------------------- 2. KIT ---
# Poids des 6 axes de lecture, par role. Un Break vit de son BREAK, un Heal de
# sa survie : le meme kit ne vaut pas la meme chose selon qui le porte.
KW = {
    "DPS":     {"dmg": .45, "team": .15, "brk": .12, "ctrl": .12, "res": .08, "sust": .08},
    "Break":   {"brk": .45, "dmg": .18, "ctrl": .12, "team": .12, "res": .08, "sust": .05},
    "Support": {"team": .40, "res": .18, "sust": .15, "ctrl": .12, "dmg": .08, "brk": .07},
    "Regen":   {"res": .40, "sust": .25, "team": .15, "ctrl": .07, "dmg": .07, "brk": .06},
    "Heal":    {"sust": .45, "team": .20, "res": .15, "ctrl": .09, "dmg": .06, "brk": .05},
}
# Penalite de conditionnalite : un kit qui empile trois conditions ne delivre
# pas les chiffres qu'il affiche. -6% par palier, -18% au maximum.
COND_PEN = 0.06

AXLABEL = {"dmg": "degats", "team": "apport d'equipe", "brk": "BREAK",
           "sust": "survie / soin", "res": "ressource EP", "ctrl": "controle"}


def rating(owner):
    """Les notes seules, sans le commentaire : deux kits notes a l'identique sont
    identiques, meme si leur phrase d'explication differe."""
    k = KITS[owner]
    return tuple([k[a] for a in AXES] + [k["cond"]])


def kit_owner(name):
    """Le kit a lire pour cette entree : le sien, ou celui de sa forme de base."""
    return KMAP["alias"].get(name, name)


def kit_score(r):
    """0..100, a partir des notes de lecture (kits.json)."""
    role = r["role"] or "DPS"
    k = KITS[kit_owner(r["name"])]
    w = KW[role]
    raw = sum(w[a] * k[a] / 10.0 for a in AXES) * 100
    pts = raw * (1 - COND_PEN * k["cond"])
    why = ["%s %d/10" % (AXLABEL[a], k[a]) for a in AXES if k[a] > 0]
    if k["cond"]:
        why.append("- conditionnalite %d/3 (-%d%%)"
                   % (k["cond"], round(COND_PEN * k["cond"] * 100)))
    return min(100.0, pts), why, k


# ------------------------------------------------------------- 3. SYNERGIE ---
# Ce qu'un Aniimo donne a l'equipe, independamment de son role affiche.
GIVE_W = {"team": .40, "sust": .20, "res": .20, "brk": .10, "ctrl": .10}
# Part de "contribution a l'equipe" vs "facilite d'insertion" selon le role.
# Un DPS ne synergise pas en buffant : il synergise en rentrant dans
# n'importe quelle composition sans condition. Noter les deux pareil
# penaliserait mecaniquement tous les DPS.
SYN_MIX = {"DPS": .35, "Break": .55, "Support": .78, "Regen": .72, "Heal": .75}
COND_FIT = {0: 34, 1: 20, 2: 10, 3: 0}


def syn_score(r, k):
    """0..100. Deux composantes : ce que l'Aniimo apporte a l'equipe, et la
    facilite avec laquelle il s'insere dans n'importe quelle composition."""
    why = []
    give = sum(GIVE_W[a] * k[a] / 10.0 for a in GIVE_W) * 100
    for a in sorted(GIVE_W, key=lambda x: -k[x]):
        if k[a] > 0:
            why.append("apporte : %s %d/10" % (AXLABEL[a], k[a]))

    fit = COND_FIT[k["cond"]]
    why.append("conditionnalite %d/3, soit %d points d'insertion"
               % (k["cond"], COND_FIT[k["cond"]]))
    if len(r["el"]) > 1:
        fit += 24
        why.append("bi-element (%s)" % "/".join(r["el"]))
    if r["stage"] in ("Nova", None):
        fit += 20
        why.append("forme finale, pas d'evolution a attendre")
    pf = (r.get("pathfinding") or "").lower()
    if any(x in pf for x in ("fly", "swim", "climb", "glide")):
        fit += 12
        why.append("mobilite d'exploration")
    if k["ctrl"] >= 5 or k["dmg"] >= 7:
        fit += 10
        why.append("utile dans n'importe quelle composition")

    m = SYN_MIX.get(r["role"] or "DPS", .5)
    return min(100.0, m * min(100, give) + (1 - m) * min(100, fit)), why


# ------------------------------------------------------------------ TOTAL ---
STAGE_MULT = {"Nova": 1.0, "Gamma": 0.90, "Lumin": 0.78}

# Rattache les formes regionales a leur Aniimo de base (affichage de famille).
BASES = {r["name"]: r for r in PLAY if r["kind"] == "base"}
parent = {}
variants = collections.defaultdict(list)
for r in PLAY:
    if r["kind"] == "form":
        for b in BASES:
            if r["name"].endswith(" " + b):
                parent[r["name"]] = b
                variants[b].append({"n": r["name"], "el": r["el"], "no": r["no"]})
                break
    elif r["kind"] == "prismana":
        b = r["name"][len("Prismana "):]
        if b in BASES:
            parent[r["name"]] = b

out = []
for r in PLAY:
    st, parts = stat_score(r)
    kt, kwhy, k = kit_score(r)
    sy, swhy = syn_score(r, k)
    # Somniwing et Irisalis n'affichent aucun stade : ce sont des Aniimo sans
    # ligne d'evolution, donc deja des formes finales -> pas de penalite.
    stage = STAGE_MULT.get(r["stage"], 1.0)
    total = (0.50 * st + 0.32 * kt + 0.18 * sy) * stage

    # Une forme strictement identique a sa base sur tous les axes mesures
    # obtient forcement le meme score : on le signale plutot que de laisser
    # croire a deux entrees reellement distinctes.
    # On compare les NOTES du kit, pas le nom du proprietaire : une Prismana est
    # toujours son propre proprietaire de kit, mais ses notes peuvent etre
    # rigoureusement celles de sa base.
    p = parent.get(r["name"])
    same = bool(p and r["stats"] == BASES[p]["stats"]
                and rating(kit_owner(r["name"])) == rating(kit_owner(p))
                and sorted(r["el"]) == sorted(BASES[p]["el"])
                and r["role"] == BASES[p]["role"])

    out.append({
        "name": r["name"], "no": r["no"], "kind": r["kind"],
        "el": r["el"], "role": r["role"], "stage": r["stage"],
        "stats": r["stats"], "total": r["total"],
        "fav": FAV[r["role"] or "DPS"],
        "sStat": round(st, 1), "sKit": round(kt, 1), "sSyn": round(sy, 1),
        "sStage": stage, "score": round(total, 1),
        "statParts": parts, "kitWhy": kwhy, "synWhy": swhy,
        "axes": {a: k[a] for a in AXES}, "cond": k["cond"],
        "kitWho": kit_owner(r["name"]), "kitNote": k["why"],
        "parent": p, "same": same, "ref": REFTIER.get(r["name"]),
        "traits": r["traits"], "skills": r["skills"], "innate": r["innate"],
        "mobility": r["mobility"], "pathfinding": r["pathfinding"],
        "homeland": r["homeland"], "log": r["log"],
        "variants": variants.get(r["name"], []),
    })

# --------- tiers calcules SEPAREMENT pour chaque roster ---------------------
# Tiers par percentile a l'interieur de chaque roster : une pyramide lisible
# plutot qu'un min-max qui ecrase tout le monde en bas.
CUT = [("S", .10), ("A", .25), ("B", .52), ("C", .80), ("D", 1.01)]


def assign(group):
    if not group:
        return
    ranked = sorted(group, key=lambda g: -g["score"])
    n = len(ranked)
    for i, g in enumerate(ranked):
        q = (i + 0.5) / n
        g["tier"] = next(t for t, th in CUT if q < th)
        g["rank"] = i + 1
        g["of"] = n


groups = {k: [g for g in out if g["kind"] == k] for k in ("base", "form", "prismana")}
for g in groups.values():
    assign(g)

out.sort(key=lambda g: -g["score"])
io.open("data.js", "w", encoding="utf-8").write(
    "const ANIIMO = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
    + "const META = " + json.dumps({
        "weights": W, "fav": FAV, "crown": CROWN, "stage": STAGE_MULT,
        "mix": {"stat": .50, "kit": .32, "syn": .18},
        "kitW": KW, "giveW": GIVE_W, "synMix": SYN_MIX, "condPen": COND_PEN,
        "condFit": COND_FIT, "axes": AXES, "axLabel": AXLABEL,
        "lo": LO, "hi": HI,
        "n": {k: len(v) for k, v in groups.items()},
        "nKits": len(KITS), "nSame": sum(1 for g in out if g["same"]),
        "cut": CUT,
        "lock": SYN["lock"], "duos": SYN["duos"], "rules": SYN["rules"],
    }, ensure_ascii=False) + ";\n")

print("base=%d  formes=%d  prismana=%d  (total %d)"
      % (len(groups["base"]), len(groups["form"]), len(groups["prismana"]), len(out)))
print("formes strictement identiques a leur base : %d" % sum(1 for g in out if g["same"]))
print("kits lus : %d | kits herites : %d" % (len(KITS), len(KMAP["alias"])))
for label in ("base", "form", "prismana"):
    c = collections.Counter(g["tier"] for g in groups[label])
    print("\n--- %s --- %s" % (label.upper(), " ".join("%s:%d" % (t, c[t]) for t, _ in CUT)))
    for g in sorted(groups[label], key=lambda x: -x["score"])[:8]:
        print("  %-24s %-8s %5.1f  (stat %4.1f kit %4.1f syn %4.1f)"
              % (g["name"], g["tier"], g["score"], g["sStat"], g["sKit"], g["sSyn"]))
