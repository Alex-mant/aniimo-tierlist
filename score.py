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

Le KIT ne vient plus d'expressions regulieres : les 122 kits distincts ont ete
lus un par un et notes sur 6 axes (voir RUBRIC.md et kits.json). Les 93 formes
regionales qui reutilisent le kit de leur base heritent de ses notes via
raw/_kitmap.json.

Ce calcul est ensuite CROISE avec six tier lists publiees (raw/_ext_tiers.json,
voir ext_tiers.py) : chaque source pese selon son accord avec les autres, le
calcul pese comme une source de plus, et un reechantillonnage donne a chaque
Aniimo un indice de confiance (sur / probable / incertain).

Sortie : data.js
"""
import json, io, collections, math, random, bisect, re, os

# Le roster classe est celui qu'assemble merge.py : les fiches Game8 telles
# quelles, plus ce que la seconde source ajoute et que Game8 n'a pas encore
# redige. Rien n'y est devine : voir merge.py et raw/_attente.json.
D = json.load(io.open("raw/roster.json", encoding="utf-8"))
ATTENTE = json.load(io.open("raw/_attente.json", encoding="utf-8"))
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
    "Support": {"reg": .37, "hp": .23, "mdef": .17, "pdef": .13, "atk": .10, "brk": 0},
    "Regen":   {"reg": .47, "hp": .23, "mdef": .14, "pdef": .11, "atk": .05, "brk": 0},
    "Heal":    {"hp": .42, "reg": .22, "mdef": .14, "pdef": .12, "atk": .10, "brk": 0},
}
# Ce que mesurent vraiment les stats (verifie dans les fiches) : REGEN est la
# recuperation d'EP, pas du soin ; les soins et boucliers s'indexent sur les PV max
# (22 soins de Heal sur 22). Un Heal vit donc de ses PV, un Regen de sa REGEN.
# Support, Regen et Heal ne cassent pas les jauges : le BREAK ne compte pas pour eux,
# ni dans leurs stats ni dans leur kit. Ce qu'ils apportent au BREAK de l'equipe
# reste visible dans le constructeur d'equipe.
# --- POTENTIEL : ce que devient une stat sur l'exemplaire parfait -----------
# Deux exemplaires d'un meme Aniimo n'ont pas les memes stats : a la capture, le
# jeu tire un POTENTIEL INNE par statistique (l'expertise le classe Commun / Bon
# / Elite / Parfait), puis l'Eveil d'aptitude laisse monter ce potentiel contre
# de la Poussiere d'etoile. Inne et acquis se partagent le meme plafond :
#   - 20 points par statistique ;
#   - 24 sur les deux statistiques que le jeu recommande, une fois l'Ascension
#     de resident passee -- ce sont elles que porte l'icone couronne, et c'est a
#     elles que le Capafruit ajoute son point ;
#   - chaque point vaut +4% de la statistique (et +6 PC).
# La tier list se place sur l'exemplaire PARFAIT, donc tout le monde est a son
# plafond : x1,80 sur une stat ordinaire, x1,96 sur une stat couronnee. La
# couronne vaut donc +8,9%, et non les +20% que suggerait le rapport 24/20 --
# c'est la correction de fond de cette version.
PT = 0.04
CAP, CAP_FAV = 20, 24
GROW, GROW_FAV = 1 + PT * CAP, 1 + PT * CAP_FAV
CROWN = GROW_FAV / GROW

# Le grade du tirage inne, tel que l'expertise le note, et les frequences
# relevees a la capture. Cela ne change rien au classement -- la tier list se
# place sur l'exemplaire parfait, donc sur le meme plafond pour tout le monde --
# mais c'est ce qui explique que deux exemplaires du meme Aniimo n'aient pas les
# memes statistiques, et ce que le joueur doit relancer pour atteindre ce plafond
# sans y laisser toute sa Poussiere d'etoile.
GRADES = [["Commun", 66.0], ["Bon", 26.0], ["Elite", 7.2], ["Parfait", 0.8]]

# Second tirage aleatoire a la capture : la PERSONNALITE (16 types facon MBTI,
# quatre creneaux de deux lettres). Elle se rejoue au Fruit de psyche : sur
# l'exemplaire parfait, c'est donc un choix et non un tirage. Elle n'entre PAS
# dans le calcul, et c'est voulu : le meilleur choix est le meme pour tous les
# Aniimo d'un meme role, or la note de stat est normalisee par role -- un bonus
# uniforme s'y annulerait exactement. Elle est publiee parce qu'elle fait partie
# de la forme parfaite que le joueur doit viser, et parce que deux de ses effets
# (degats, critique, reduction) ne sont meme pas des statistiques.
PERSO = [
    [["E", "Énergique", "ATQ +2%, BREAK +2%"], ["I", "Instinctif", "REGEN +4%"]],
    [["S", "Pratique", "Dégâts +4%"], ["N", "Agile", "Taux critique +5%"]],
    [["T", "Tenace", "DEF.P +6%"], ["F", "Fidèle", "DEF.M +6%"]],
    [["J", "Judicieux", "PV +4%"], ["P", "Joueur", "Réduction de dégâts +4%"]],
]
PERSO_BEST = {"DPS": "EN", "Break": "ES", "Support": "IJ", "Regen": "IJ", "Heal": "IJ"}

PLAY = [r for r in D if r["kind"] in ("base", "form", "prismana")]

# Quelles stats sont couronnables ? Le jeu le dit PAR ANIIMO, pas par role, et
# merge.py a reporte cette donnee dans "reco" (103 entrees sur 215). Pour les
# autres, il faut bien un defaut : on prend les deux stats que le jeu recommande
# le plus souvent AU SEIN DU MEME ROLE, comptees sur les fiches ou il les a
# reellement publiees. C'est un defaut mesure, pas suppose -- et il est affiche
# comme tel sur la fiche ("defaut de role" au lieu du nom de la fiche source).
def _fav_defaut():
    cnt, vu = collections.defaultdict(collections.Counter), set()
    for r in PLAY:
        src = r.get("recoOf")
        if not src or src in vu or not r["role"]:
            continue
        vu.add(src)
        for st in r["reco"]:
            cnt[r["role"]][st] += 1
    out = {}
    for role in W:
        c = cnt.get(role)
        # a defaut de tout releve, les deux stats les plus lourdes du role
        ordre = sorted(STATS, key=lambda st: (-(c[st] if c else 0), -W[role][st]))
        out[role] = sorted(ordre[:2])
    return out


FAV = _fav_defaut()


def fav_of(r):
    """Les deux stats couronnables de CET Aniimo."""
    return r["reco"] or FAV[r["role"] or "DPS"]


def grown(r, s):
    """La statistique de l'exemplaire parfait, potentiel pousse a son plafond."""
    return r["stats"][s] * (GROW_FAV if s in fav_of(r) else GROW)


# Normalisation en PERCENTILE sur tout le roster jouable : un min-max laisse un
# seul extreme (un PV hors norme) ecraser toute l'echelle. Le percentile porte
# sur la valeur POUSSEE, pas sur la stat de base : c'est elle qu'on compare.
LO = {s: min(r["stats"][s] for r in PLAY) for s in STATS}
HI = {s: max(r["stats"][s] for r in PLAY) for s in STATS}
SORTED = {s: sorted(grown(r, s) for r in PLAY) for s in STATS}


def pctl(s, v):
    a = SORTED[s]
    lt, le = bisect.bisect_left(a, v), bisect.bisect_right(a, v)
    return (lt + .5 * (le - lt)) / len(a)


def stat_score(r):
    """0..100. Stats de l'exemplaire parfait (potentiel au plafond, couronne
    comprise) en percentile du roster, ponderees par le role."""
    w = W[r["role"] or "DPS"]
    tot = 0.0
    parts = {}
    for s in STATS:
        n = pctl(s, grown(r, s))
        parts[s] = round(n * 100, 1)
        tot += w[s] * n
    return min(100.0, tot * 100), parts


# ----------------------------------------------------------------- 2. KIT ---
# Poids des 6 axes de lecture, par role. Un Break vit de son BREAK, un Heal de
# ses soins, un Regen de l'EP qu'il rend a l'equipe (Regen = recharge d'EP, PAS
# du soin) : le meme kit ne vaut pas la meme chose selon qui le porte.
KW = {
    "DPS":     {"dmg": .45, "team": .15, "brk": .12, "ctrl": .12, "res": .08, "sust": .08},
    "Break":   {"brk": .45, "dmg": .18, "ctrl": .12, "team": .12, "res": .08, "sust": .05},
    "Support": {"team": .43, "res": .19, "sust": .16, "ctrl": .13, "dmg": .09, "brk": 0},
    "Regen":   {"res": .48, "team": .18, "ctrl": .12, "dmg": .12, "sust": .10, "brk": 0},
    "Heal":    {"sust": .47, "team": .21, "res": .16, "ctrl": .10, "dmg": .06, "brk": 0},
}
# Penalite de conditionnalite : un kit qui empile trois conditions ne delivre
# pas les chiffres qu'il affiche. -6% par palier, -18% au maximum.
COND_PEN = 0.06

# Deux sorts equipes a la fois, pas plus. Les notes de kits.json lisent le kit
# ENTIER ; kit_skills.json dit, pour chaque sort (et pour la part toujours active :
# ultime, attaque de base, traits), quelle part de chaque axe il porte (0..3).
# On garde, par kit, la paire de sorts qui vaut le plus pour son role, et chaque
# axe est ramene a ce que cette paire + la part fixe delivrent. Cumul en "OU
# bruite" (p = w/5) : l'echelle de lecture sature, deux sources moyennes ne valent
# pas le double d'une seule, mais retirer la seule source d'un axe le vide.
EQUIP = 2
_TAGS = json.load(io.open("kit_skills.json", encoding="utf-8"))


def _tags():
    """kit_skills.json note les COMPETENCES, pas les couples (Aniimo, competence).
    Une meme competence ne peut donc plus recevoir deux notes selon qui la lance.
    On reconstitue ici la vue par proprietaire dont le reste du calcul a besoin,
    en resolvant chaque competence sur son texte de jeu exact : un nom porte
    plusieurs notations uniquement s'il porte plusieurs textes (Ballistic Guard,
    lignee Helmut contre lignee Rookey)."""
    cat, out = _TAGS["skills"], {}
    for o, v in _TAGS["owners"].items():
        out[o] = {"always": v["always"], "skills": {}}
    for r in D:
        o = r["name"]
        if o not in out:
            continue
        for s in r.get("skills") or []:
            e = cat.get(s["n"])
            if e is None:
                raise SystemExit("competence absente de la table : %s / %s" % (o, s["n"]))
            if "variants" in e:
                d = (s.get("d") or "").strip()
                e = next((x for x in e["variants"] if x["when"] == d), None)
                if e is None:
                    raise SystemExit("texte non reconnu : %s / %s" % (o, s["n"]))
            out[o]["skills"][s["n"]] = e
    return out


TAGS = _tags()
KITS_ALL = {o: dict(k) for o, k in KITS.items()}
LOADOUT = {}
# Un sort dont l'effet ne vise qu'un element allie (Nebula Burst : degats Tenebres
# des allies ; Lightning Surge : allies Foudre) porte dans kit_skills.json un
# "lock" {el, off} : ses notes "off" valent quand aucun allie n'a cet element.
# LOADOUT_EL liste la meilleure paire pour chaque jeu d'elements allies presents ;
# le constructeur d'equipe prend celle que la composition autorise.
ELS = "Fire|Water|Grass|Wind|Dark|Light|Ice|Earth|Lightning"
LOCK_RE = [re.compile(r"(?:teammates'|allies'|team's) (%s) damage" % ELS),
           re.compile(r"(%s)[- ](?:type|element) (?:teammates|allies)" % ELS)]
LOADOUT_EL = {}
NEED_OFF = 0.5
ADD_AXES = tuple(x for x in os.environ.get("AMO_ADD", "dmg,brk").split(",") if x)


ULT_RE = re.compile(r"(%s) Elemental Boost for (?:all )?team members|entire team \d+%% (%s) Elemental Boost" % (ELS, ELS))


def ult_el(r):
    """Element dope pour toute l'equipe par l'ultime (Fragrancier : Tenebres)."""
    m = ULT_RE.search(" ".join(x.get("d", "") for x in r.get("innate") or []))
    return m and (m.group(1) or m.group(2))


def _reach(parts):
    s = 1.0
    for w in parts:
        s *= 1 - w / 5.0
    return 1 - s


def _equip():
    role_of = {r["name"]: r["role"] or "DPS" for r in D}
    sk_of = {r["name"]: list(dict.fromkeys(s["n"] for s in r["skills"])) for r in D}   # un sort liste deux fois
    by_name = {}
    for r in D:
        by_name.setdefault(r["name"], r)
    for o, k in KITS_ALL.items():
        names = sk_of[o]
        if len(names) <= EQUIP or o not in TAGS:
            LOADOUT[o] = names
            continue
        t = TAGS[o]
        desc = {s["n"]: s["d"] for s in by_name[o]["skills"]}
        for n in names:   # garde-fou : un texte "allies X" sans lock annote
            m = next((x.search(desc[n]) for x in LOCK_RE if x.search(desc[n])), None)
            if m and t["skills"][n].get("lock", {}).get("el") != m.group(1):
                print("  ! lock manquant : %s / %s (%s)" % (o, n, m.group(1)))
        locks = {n: t["skills"][n]["lock"] for n in names if "lock" in t["skills"][n]}
        w = KW[role_of[o]]
        full = {a: _reach([t["always"][a]] + [t["skills"][n][a] for n in names]) for a in AXES}
        top = {a: t["always"][a] + sum(sorted((t["skills"][n][a] for n in names), reverse=True)[:EQUIP])
               for a in ADD_AXES}

        def share(a, parts):
            if a in ADD_AXES:     # les degats s'additionnent : 2e sort de degats = 2e source
                return sum(parts) / top[a] if top[a] > 0 else 1.0
            return _reach(parts) / full[a] if full[a] > 0 else 1.0

        def best_pair(on, must=()):
            def tag(n, a, L):
                lk, sk = locks.get(n), t["skills"][n]
                v = lk["off"][a] if lk and lk["el"] not in on else sk[a]
                # consomme une marque que seul un autre sort pose (Critical Hit / Claw of Madness)
                return v * NEED_OFF if sk.get("needs") and not set(sk["needs"]) & set(L) else v
            best = None
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    L = (names[i], names[j])
                    if any(not any(locks.get(n, {}).get("el") == e for n in L) for e in must):
                        continue
                    ax = {a: round(k[a] * share(a, [t["always"][a]] + [tag(n, a, L) for n in L]), 1) for a in AXES}
                    v = sum(w[a] * ax[a] for a in AXES)
                    if best is None or v > best[0] + 1e-9:
                        best = (v, L, ax)
            return best
        els = sorted({lk["el"] for lk in locks.values()})
        best = best_pair(set(els))        # tier list : l'equipe qui lui convient
        LOADOUT[o] = list(best[1])
        KITS[o] = dict(k, **best[2])
        if not locks:
            continue
        vars_ = {}
        for m in sorted(range(1 << len(els)), key=lambda x: bin(x).count("1")):
            on = {e for i, e in enumerate(els) if m >> i & 1}
            # la meilleure paire, et celle qui sert vraiment ces allies (le combo d'equipe peut la preferer)
            for v in filter(None, (best_pair(on), best_pair(on, must=on))):
                uses = [n for n in v[1] if n in locks and locks[n]["el"] in on]
                need = sorted({locks[n]["el"] for n in uses})
                vars_.setdefault(v[1], {"need": need, "equip": list(v[1]), "axes": v[2]})   # need minimal en premier
        LOADOUT_EL[o] = {"locks": {n: lk["el"] for n, lk in locks.items()},
                         "vars": sorted(vars_.values(), key=lambda x: len(x["need"]))}


_equip()

# noms d'elements tels qu'ils s'affichent sur le site (voir ELAB dans index.html)
ELLABEL = {"Fire": "Feu", "Water": "Eau", "Grass": "Herbe", "Wind": "Vent",
           "Earth": "Terre", "Ice": "Glace", "Lightning": "Foudre",
           "Dark": "Ténèbres", "Light": "Lumière"}

AXLABEL = {"dmg": "dégâts", "team": "apport d'équipe", "brk": "BREAK",
           "sust": "survie / soin", "res": "ressource EP", "ctrl": "contrôle"}


def rating(owner):
    """Les notes seules, sans le commentaire : deux kits notes a l'identique sont
    identiques, meme si leur phrase d'explication differe."""
    k = KITS_ALL[owner]
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
        why.append("- conditionnalité %d/3 (-%d%%)"
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
# Insertion : base 40, +30 bi-element, +30 si utile partout (controle ou gros degats).
# Ne comptent plus : la mobilite d'exploration (hors combat), la forme finale (deja
# dans le multiplicateur de stade) et la conditionnalite (deja retiree du kit).
FIT = {"base": 40, "dual": 30, "any": 30}


def syn_score(r, k):
    """0..100. Deux composantes : ce que l'Aniimo apporte a l'equipe, et la
    facilite avec laquelle il s'insere dans n'importe quelle composition."""
    why = []
    give = sum(GIVE_W[a] * k[a] / 10.0 for a in GIVE_W) * 100
    for a in sorted(GIVE_W, key=lambda x: -k[x]):
        if k[a] > 0:
            why.append("apporte : %s %d/10" % (AXLABEL[a], k[a]))
    fit = FIT["base"]
    if len(r["el"]) > 1:
        fit += FIT["dual"]
        why.append("bi-élément (%s)" % "/".join(ELLABEL.get(e, e) for e in r["el"]))
    if k["ctrl"] >= 5 or k["dmg"] >= 7:
        fit += FIT["any"]
        why.append("utile dans n'importe quelle composition")
    m = SYN_MIX.get(r["role"] or "DPS", .5)
    return min(100.0, m * min(100, give) + (1 - m) * min(100, fit)), why


# ------------------------------------------------------------------ TOTAL ---
STAGE_MULT = {"Nova": 1.0, "Gamma": 0.90, "Lumin": 0.78}
MIX = {"stat": .50, "kit": .32, "syn": .18}
ROLES = ["DPS", "Break", "Support", "Regen", "Heal"]
# Normalisation par role : chaque composante est recentree dans son role (moyenne
# 50, ecart-type 15), sinon un role entier finit en bas parce que ses stats
# "naturelles" sont plus basses. Moyenne et ecart-type sont retrecis vers le global
# (SHRINK entrees fictives) : un role de 11 membres ne donne qu'une estimation
# bruitee. Calcules sur les entrees DISTINCTES (formes identiques ecartees).
SHRINK = 10

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


def skillset(r):
    """Les competences telles que le jeu les donne : nom ET texte. Prismana
    Inferlupa a un sort de plus que sa base (Blazing Wolf Assault) et son attaque
    de base perd le marqueur (BREAK) ; elle n'est donc PAS identique, meme si ses
    stats et ses notes coincident."""
    return (sorted((s["n"], (s.get("d") or "").strip()) for s in r.get("skills") or []),
            sorted((x.get("n"), (x.get("d") or "").strip()) for x in r.get("innate") or []))


def is_same(r):
    """Forme strictement identique a sa base sur tout ce que le jeu expose. On
    compare les notes LUES A LA MAIN (KITS_ALL) et non KITS, que l'optimisation de
    loadout a reecrit en flottants : deux kits identiques y divergent au dixieme."""
    p = parent.get(r["name"])
    return bool(p and r["stats"] == BASES[p]["stats"]
                and rating(kit_owner(r["name"])) == rating(kit_owner(p))
                and sorted(r["el"]) == sorted(BASES[p]["el"])
                and r["role"] == BASES[p]["role"]
                and skillset(r) == skillset(BASES[p]))


SAME = {r["name"]: is_same(r) for r in PLAY}


def _stat(r, w):
    tot = det = 0.0
    for s in STATS:
        tot += w[s] * pctl(s, grown(r, s)); det += w[s]
    return min(100.0, tot / det * 100) if det else 0.0


def model(w_stat=W, w_kit=KW, mix=MIX, kits=None):
    """Score du calcul pour tout le roster : {nom: (score, stat, kit, syn bruts)}.
    `kits` remplace les notes de kit (tests de robustesse)."""
    raw = {}
    for r in PLAY:
        role = r["role"] or "DPS"
        k = (kits or KITS)[kit_owner(r["name"])]
        st = _stat(r, w_stat[role])
        kt = min(100.0, sum(w_kit[role][a] * k[a] / 10.0 for a in AXES) * 100 * (1 - COND_PEN * k["cond"]))
        sy = syn_score(r, k)[0]
        raw[r["name"]] = [st, kt, sy]
    brut = {n: tuple(v) for n, v in raw.items()}
    for c in range(3):
        allv = [v[c] for v in brut.values()]
        gm = sum(allv) / len(allv)
        gs = math.sqrt(sum((x - gm) ** 2 for x in allv) / len(allv))
        for R in ROLES:
            mem = [r["name"] for r in PLAY if (r["role"] or "DPS") == R]
            vs = [brut[n][c] for n in mem if not SAME[n]]
            if not vs:
                continue
            n = len(vs); m = sum(vs) / n
            sd = math.sqrt(sum((x - m) ** 2 for x in vs) / n) or gs
            m2 = (n * m + SHRINK * gm) / (n + SHRINK); sd2 = (n * sd + SHRINK * gs) / (n + SHRINK)
            for nm in mem:
                raw[nm][c] = 50 + 15 * (brut[nm][c] - m2) / sd2
    tot = sum(mix.values())
    out = {}
    for r in PLAY:
        st, kt, sy = raw[r["name"]]
        sc = (mix["stat"] * st + mix["kit"] * kt + mix["syn"] * sy) / tot * STAGE_MULT.get(r["stage"], 1.0)
        out[r["name"]] = (sc,) + brut[r["name"]]
    return out


def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); rk = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for q in range(i, j + 1):
            rk[o[q]] = (i + j) / 2
        i = j + 1
    return rk


def spear(x, y):
    rx, ry = rank(x), rank(y); n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    c = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    d = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return c / d if d else 0.0


def pctmap(sc):
    """{nom: score} -> {nom: percentile 0..1 (1 = meilleur)}, ex aequo moyennes."""
    names = list(sc); rk = rank([sc[n] for n in names])
    return {n: (rk[i] + .5) / len(names) for i, n in enumerate(names)}


# ------------------------------------------------ 4. CROISEMENT DES SOURCES ---
# Six tier lists publiees (voir ext_tiers.py). Chaque source est ramenee en
# percentile de rang A L'INTERIEUR d'elle-meme : peu importe qu'elle ait 4 ou 7
# paliers, ou qu'elle mette la moitie du roster en S, seul l'ordre compte.
EXT = json.load(io.open("raw/_ext_tiers.json", encoding="utf-8"))
SRCS = sorted(EXT)
PCT = {s: pctmap(EXT[s]["pos"]) for s in SRCS}
LABEL = {s: {n: EXT[s]["levels"][round((1 - p) * (len(EXT[s]["levels"]) - 1))]
             for n, p in EXT[s]["pos"].items()} for s in SRCS}


# Un groupe d'identite = une base et les formes que le jeu lui donne a
# l'identique (memes stats, memes elements, meme role, memes notes de kit, memes
# competences). Pour le jeu c'est un seul Aniimo ; une source qui le liste deux
# fois a des places differentes emet deux avis sur la MEME chose. On en prend la
# moyenne et on la donne a tout le groupe : sans cela une Prismana se retrouvait
# classee sous sa base alors que rien ne les distingue.
GROUP = {}
for _r in PLAY:
    _p = parent.get(_r["name"])
    GROUP.setdefault(_p if (_p and SAME[_r["name"]]) else _r["name"], []).append(_r["name"])
for _h, _m in list(GROUP.items()):
    if _h not in _m:
        _m.insert(0, _h)
GRP = {n: GROUP[h] for h, m in GROUP.items() for n in m}


def opinions(name):
    """Les avis sur cette entree : ceux de son groupe d'identite, moyennes."""
    grp = GRP.get(name, [name])
    out = {}
    for s in SRCS:
        hits = [k for k in grp if k in PCT[s]]
        if not hits:
            continue
        p = sum(PCT[s][k] for k in hits) / len(hits)
        lab = LABEL[s][name] if name in hits else LABEL[s][hits[0]]
        out[s] = (p, lab, name not in hits)
    return out


OPI = {r["name"]: opinions(r["name"]) for r in PLAY}


def src_weight(s, pool=None):
    """Fiabilite d'une source = (accord de rang avec la moyenne des AUTRES)^2.
    Une source qui classe au hasard pese ~0 ; deux sources qui se copient ne se
    valident pas mutuellement, puisque chacune est jugee contre toutes les autres."""
    pool = pool or SRCS
    others = [o for o in pool if o != s]
    com = [n for n in PCT[s] if sum(n in PCT[o] for o in others) >= 2]
    cons = [sum(PCT[o][n] for o in others if n in PCT[o]) / sum(n in PCT[o] for o in others) for n in com]
    return max(.05, spear([PCT[s][n] for n in com], cons)) ** 2


SRCW = {s: src_weight(s) for s in SRCS}


def blend(mp, wm, srcw=SRCW):
    """Percentile final = moyenne ponderee du calcul et des sources qui classent
    l'entree. Sans aucune source, c'est le calcul seul."""
    out = {}
    for n in mp:
        num, den = wm * mp[n], wm
        for s, (p, _, _) in OPI[n].items():
            if s in srcw:
                num += srcw[s] * p; den += srcw[s]
        out[n] = num / den if den else mp[n]
    return out


M0 = model()
MP = pctmap({n: v[0] for n, v in M0.items()})
_c = {n: sum(SRCW[s] * OPI[n][s][0] for s in OPI[n]) / sum(SRCW[s] for s in OPI[n])
      for n in MP if len(OPI[n]) >= 2}
# Le calcul pese comme une source : son accord avec le consensus, au carre.
WM = max(.05, spear([MP[n] for n in _c], [_c[n] for n in _c])) ** 2
FIN = blend(MP, WM)

CUT = [("S", .10), ("A", .25), ("B", .52), ("C", .80), ("D", 1.01)]
ORDER = [t for t, _ in CUT]


def tiers_of(sc):
    """Decoupe par quantile -- mais une coupure ne passe jamais entre deux notes
    EGALES. Trois formes d'un meme Aniimo qui partagent stats et kit ont la meme
    note a la decimale pres : les separer parce que la frontiere des 10 % tombe
    au milieu du paquet serait un artefact du decoupage, pas un jugement. Tout
    ex aequo suit donc le premier de son groupe."""
    ranked = sorted(sc, key=lambda n: -sc[n]); n = len(ranked)
    out, i = {}, 0
    while i < n:
        j = i
        while j + 1 < n and sc[ranked[j + 1]] == sc[ranked[i]]:
            j += 1
        t = next(t for t, th in CUT if (i + .5) / n < th)
        for k in range(i, j + 1):
            out[ranked[k]] = t
        i = j + 1
    return out


TIER = tiers_of(FIN)

# Validation : chaque source est predite par le calcul melange aux AUTRES sources,
# et comparee a ce que les autres sources en disent entre elles.
VALID, WLOO = {}, {}
for s in SRCS:
    others = [o for o in SRCS if o != s]
    w2 = WLOO[s] = {o: round(src_weight(o, others), 4) for o in others}
    f2 = blend(MP, WM, w2)
    names = list(PCT[s])
    peers = {n: sum(w2[o] * PCT[o][n] for o in others if n in PCT[o]) / sum(w2[o] for o in others if n in PCT[o])
             for n in names if any(n in PCT[o] for o in others)}
    pn = list(peers)
    VALID[s] = {"n": len(names),
                "model": round(spear([MP[n] for n in names], [PCT[s][n] for n in names]), 3),
                "final": round(spear([f2[n] for n in names], [PCT[s][n] for n in names]), 3),
                "peers": round(spear([peers[n] for n in pn], [PCT[s][n] for n in pn]), 3)}

# --------------------------------------------------- 5. INDICE DE CONFIANCE ---
# RUNS tirages ou TOUT ce qui est incertain bouge a la fois :
#  - chaque poids du calcul perturbe de +-25 %,
#  - chaque note de kit relue par un autre lecteur (+-1 avec probabilite 2/3),
#  - les 7 avis (6 sources + le calcul) reechantillonnes avec remise : on se
#    demande ce qu'aurait donne le classement avec d'autres sources.
# SUR : garde son palier dans au moins 75 % des tirages ET classe par au moins deux
# sources. INCERTAIN : aucune source ne l'a classe, ou ses tirages s'etalent sur
# trois paliers. PROBABLE : le reste (en general, a cheval entre deux paliers).
RUNS = 400
rng = random.Random(2026)
jit = lambda v: v * (.75 + rng.random() * .5)
dist = {n: collections.Counter() for n in FIN}
for _ in range(RUNS):
    ws = {R: {k: jit(v) for k, v in W[R].items()} for R in W}
    wk = {R: {k: jit(v) for k, v in KW[R].items()} for R in KW}
    mx = {k: jit(v) for k, v in MIX.items()}
    ks = {o: dict(k, **{a: max(0, min(10, k[a] + rng.choice((-1, 0, 1)))) for a in AXES}) for o, k in KITS.items()}
    mp = pctmap({n: v[0] for n, v in model(ws, wk, mx, ks).items()})
    pick = collections.Counter(rng.choice(SRCS + ["_calc"]) for _ in range(len(SRCS) + 1))
    w2 = {s: SRCW[s] * pick[s] for s in SRCS if pick[s]}
    t = tiers_of(blend(mp, WM * pick["_calc"], w2))
    for n in t:
        dist[n][t[n]] += 1


def confidence(n):
    d = dist[n]; keep = d[TIER[n]] / RUNS
    # plus petit intervalle de paliers contigus, contenant le palier affiche,
    # qui couvre 80 % des tirages
    best = None; ti = ORDER.index(TIER[n])
    for i in range(ti + 1):
        for j in range(ti, 5):
            if sum(d[t] for t in ORDER[i:j + 1]) >= .8 * RUNS and (best is None or j - i < best[1] - best[0]):
                best = (i, j)
    span = ORDER[best[0]:best[1] + 1]
    nsrc = len(OPI[n])
    # Le seuil porte sur le taux ARRONDI, celui que la page affiche : un Aniimo
    # annonce a 75 % ne doit pas etre dit "probable" parce que le calcul exact
    # valait 74,8. Le badge et le pourcentage lu a cote disent alors la meme chose.
    pct = round(keep * 100)
    if nsrc == 0 or len(span) >= 3:
        lvl = "incertain"
    elif pct >= 75 and nsrc >= 2:
        lvl = "sur"
    else:
        lvl = "probable"
    return lvl, pct, span


out = []
for r in PLAY:
    st, parts = stat_score(r)
    kt, kwhy, k = kit_score(r)
    sy, swhy = syn_score(r, k)
    # Somniwing et Irisalis n'affichent aucun stade : ce sont des Aniimo sans
    # ligne d'evolution, donc deja des formes finales -> pas de penalite.
    stage = STAGE_MULT.get(r["stage"], 1.0)
    n = r["name"]
    lvl, keep, span = confidence(n)
    out.append({
        "name": n, "no": r["no"], "kind": r["kind"],
        "el": r["el"], "role": r["role"], "stage": r["stage"],
        "stats": r["stats"], "total": r["total"],
        "fav": fav_of(r), "reco": r["reco"], "recoOf": r["recoOf"],
        "grown": {s: round(grown(r, s), 1) for s in STATS},
        "sStat": round(st, 2), "sKit": round(kt, 2), "sSyn": round(sy, 2),
        "sStage": stage, "score": round(M0[n][0], 2), "fin": round(FIN[n], 4), "tier": TIER[n],
        "statParts": parts, "kitWhy": kwhy, "synWhy": swhy,
        "axes": {a: k[a] for a in AXES}, "cond": k["cond"],
        "axesAll": {a: KITS_ALL[kit_owner(n)][a] for a in AXES}, "equip": LOADOUT[kit_owner(n)],
        "equipEl": LOADOUT_EL.get(kit_owner(n)),
        "ultEl": ult_el(r),
        "kitWho": kit_owner(n), "kitNote": k["why"],
        "parent": parent.get(n), "same": SAME[n], "ref": REFTIER.get(n),
        # avis externes : {source: [percentile, palier affiche, herite de la base]}
        "ext": {s: [round(p, 4), lab, inh] for s, (p, lab, inh) in OPI[n].items()},
        "conf": lvl, "keep": keep, "span": span,
        "dist": {t: round(dist[n][t] / RUNS, 3) for t in ORDER if dist[n][t]},
        "traits": r["traits"], "skills": r["skills"], "innate": r["innate"],
        "mobility": r["mobility"], "pathfinding": r["pathfinding"],
        "homeland": r["homeland"], "log": r["log"],
        "variants": variants.get(n, []),
    })

groups = {k: [g for g in out if g["kind"] == k] for k in ("base", "form", "prismana")}
out.sort(key=lambda g: -g["fin"])
io.open("data.js", "w", encoding="utf-8").write(
    "const ANIIMO = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
    + "const META = " + json.dumps({
        "weights": W, "fav": FAV, "crown": round(CROWN, 4), "stage": STAGE_MULT,
        "pot": {"pt": PT, "cap": CAP, "capFav": CAP_FAV,
                "grow": round(GROW, 4), "growFav": round(GROW_FAV, 4),
                "nReco": sum(1 for g in out if g["reco"]),
                "grades": GRADES, "perso": PERSO, "persoBest": PERSO_BEST},
        "mix": MIX, "shrink": SHRINK, "fit": FIT,
        "kitW": KW, "giveW": GIVE_W, "synMix": SYN_MIX, "condPen": COND_PEN,
        "axes": AXES, "axLabel": AXLABEL,
        "lo": LO, "hi": HI,
        "n": {k: len(v) for k, v in groups.items()},
        "nKits": len(KITS), "nSame": sum(1 for g in out if g["same"]),
        "cut": CUT,
        "modelW": round(WM, 4),
        "src": {s: {"url": EXT[s]["url"], "levels": EXT[s]["levels"], "w": round(SRCW[s], 4),
                    "n": len(EXT[s]["pos"])} for s in SRCS},
        "valid": VALID, "wLoo": WLOO, "runs": RUNS,
        "lock": SYN["lock"], "duos": SYN["duos"], "rules": SYN["rules"],
        # Annonces par le jeu, pas encore classables : le site les nomme au
        # lieu de leur inventer un role ou des statistiques (voir merge.py).
        "attente": ATTENTE,
    }, ensure_ascii=False) + ";\n")

print("base=%d  formes=%d  prismana=%d  (total %d)"
      % (len(groups["base"]), len(groups["form"]), len(groups["prismana"]), len(out)))
print("poids des sources :", {s: round(v, 2) for s, v in SRCW.items()}, "| calcul : %.2f" % WM)
print("validation (predire une source sans la voir) :")
for s, v in VALID.items():
    print("  %-11s n=%3d  calcul seul %.2f | final %.2f | les autres sources entre elles %.2f"
          % (s, v["n"], v["model"], v["final"], v["peers"]))
c = collections.Counter((g["tier"], g["conf"]) for g in out)
for t in ORDER:
    print("  %s : %2d  (sur %d, probable %d, incertain %d)" % (
        t, sum(c[(t, l)] for l in ("sur", "probable", "incertain")), c[(t, "sur")], c[(t, "probable")], c[(t, "incertain")]))
for g in out[:24]:
    print("  %s %-26s %.3f %-9s garde %3d%%  %s  sources %d"
          % (g["tier"], g["name"], g["fin"], g["conf"], g["keep"], "/".join(g["span"]), len(g["ext"])))
