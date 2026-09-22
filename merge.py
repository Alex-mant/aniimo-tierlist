# -*- coding: utf-8 -*-
"""Assemble le roster que score.py classe : raw/parsed.json + raw/parsed_aniidex.json
-> raw/roster.json, et raw/_attente.json pour ce qui n'est pas encore classable.

Regle unique, et elle ne bouge pas : **aniidex n'ecrase jamais Game8**. Une fiche
deja publiee par Game8 est reprise telle quelle -- c'est sur elle qu'est calee la
notation, et les desaccords entre les deux sources sont laisses a audit.py, qui
ne tranche pas davantage. aniidex ne fait qu'AJOUTER ce que Game8 n'a pas encore
redige : Game8 s'arrete au No. 083, le jeu est alle plus loin.

Un Aniimo n'entre dans le roster que si le jeu en a publie de quoi le classer :
role, elements, statistiques, competences. Ceux dont le role n'est pas encore
publie ne sont pas devines -- ils partent dans raw/_attente.json et le site les
affiche comme annonces, pas classes.

Les formes regionales n'ont pas de page chez aniidex : la fiche de base porte une
tuile par forme, et cette tuile ne dit qu'une chose, les elements de la forme.
C'est donc tout ce qu'on en tire, le reste etant celui de la base. Ce report est
verifie : sur les 119 formes que les deux sources ont en commun, les elements lus
dans les tuiles coincident avec Game8 **119 fois sur 119**.

    python merge.py
"""
import io, json, collections

G = json.load(io.open("raw/parsed.json", encoding="utf-8"))
A = json.load(io.open("raw/parsed_aniidex.json", encoding="utf-8"))

CLASSABLE = ("role", "el", "skills", "stats")
# libelle affiche sur le site pour chaque champ manquant
LIBELLE = {"role": "rôle", "el": "élément", "skills": "compétences", "stats": "statistiques"}
have = {r["name"] for r in G}
g_stats = {r["name"]: r["stats"] for r in G}


def non_attestees():
    """Une ligne de statistiques qu'aniidex prete a PLUSIEURS Aniimo distincts
    alors que Game8 la dement pour au moins l'un d'eux n'est pas une donnee : le
    site l'a recopiee d'une fiche sur les voisines. Les fiches qui la portent et
    que Game8 ne publie pas ne peuvent donc pas etre classees dessus.

    Au releve du 21/09/2026, cela ne touche qu'une seule ligne, celle de la
    famille Lumiere : aniidex donne 100/116/72/90/72/64 a Lunara, Fennelun,
    Helion ET Soleon, et Game8 contredit les trois qu'il publie. C'est aussi la
    raison pour laquelle la statistique d'attaque de Lunara n'est PAS corrigee
    sur la foi d'aniidex : cette source ne sait rien de particulier sur Lunara,
    elle applique la meme ligne a toute la famille."""
    par_ligne = collections.defaultdict(list)
    for r in A:
        par_ligne[tuple(sorted(r["stats"].items()))].append(r["name"])
    out = {}
    for ligne, noms in par_ligne.items():
        if len(noms) < 2:
            continue
        if any(n in g_stats and g_stats[n] != dict(ligne) for n in noms):
            for n in noms:
                out[n] = sorted(noms)
    return out


SUSPECTE = non_attestees()
roster = list(G)
attente, ajouts, formes = [], [], []


def classable(r):
    return [LIBELLE[k] for k in CLASSABLE if not r.get(k)]


for r in sorted(A, key=lambda x: (x["no"] or "", x["name"])):
    if r["name"] in have:
        continue
    manque = classable(r)
    if r["name"] in SUSPECTE:
        manque.append("stats non attestées (ligne partagée avec %s)"
                      % ", ".join(n for n in SUSPECTE[r["name"]] if n != r["name"]))
    if manque:
        attente.append({"name": r["name"], "no": r["no"], "el": r["el"],
                        "stage": r["stage"], "stats": r["stats"], "total": r["total"],
                        "src": "aniidex", "manque": manque,
                        "formes": [f[0] for f in r["forms"] or []]})
        continue
    base = dict(r, kind="base", forms=[[f[0], None] for f in r["forms"] or []],
                recoOf=r["name"] if r["reco"] else None)
    roster.append(base)
    ajouts.append(r["name"])
    for lab, els in r["forms"] or []:
        n = "%s %s" % (lab, r["name"])
        if n in have or not els:
            continue
        # Seuls les elements changent ; stats, competences et innes restent ceux
        # de la base, c'est ce que la fiche montre quand on clique la tuile.
        roster.append(dict(r, name=n, no=None, el=els,
                           kind="prismana" if lab == "Prismana" else "form",
                           forms=[], recoOf=r["name"] if r["reco"] else None))
        formes.append(n)

# Les deux statistiques recommandees par le jeu -- le pouce vert de l'hexagone --
# ne sont publiees que par aniidex, et seulement sur 57 fiches. Elles valent pour
# l'Aniimo, pas pour son role : c'est sur elles que le jeu leve le plafond de
# potentiel (24 au lieu de 20, l'icone couronne) et c'est a elles que le Capafruit
# ajoute son point. On les reporte donc sur les fiches Game8 de meme nom, et les
# formes regionales heritent de leur base -- la recommandation est portee par
# l'espece, une forme n'a pas de fiche a elle chez aniidex. "recoOf" garde le nom
# de la fiche ou la recommandation a ete lue, pour que le site puisse le dire ;
# il vaut None quand le jeu ne l'a pas publiee, et on ne la devine pas ici.
A_reco = {r["name"]: r["reco"] for r in A if r.get("reco")}
alias = json.load(io.open("raw/_kitmap.json", encoding="utf-8"))["alias"]
souches = sorted({r["name"] for r in roster}, key=len, reverse=True)


def souche(nom):
    """La base dont ce nom est une forme. L'alias de raw/_kitmap.json ne couvre
    que les formes qui REUTILISENT le kit de leur base : les Prismana ont le leur,
    elles n'y figurent donc pas. On retombe sur le nom, qui est toujours
    "<libelle de forme> <base>", en prenant la base la plus longue qui le termine."""
    if nom in alias:
        return alias[nom]
    for b in souches:
        if nom != b and nom.endswith(" " + b):
            return b
    return None


for r in roster:
    if r.get("reco"):
        continue
    src = r["name"] if r["name"] in A_reco else souche(r["name"])
    r["reco"] = A_reco.get(src, [])
    r["recoOf"] = src if r["reco"] else None

io.open("raw/roster.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps(roster, ensure_ascii=False, indent=1))
io.open("raw/_attente.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps(attente, ensure_ascii=False, indent=1))

c = collections.Counter(r["kind"] for r in roster)
print("roster %d entrees : base=%d formes=%d prismana=%d"
      % (len(roster), c["base"], c["form"], c["prismana"]))
print("ajoutes par aniidex (%d) : %s" % (len(ajouts), ", ".join(ajouts)))
print("formes deduites des tuiles (%d) : %s" % (len(formes), ", ".join(formes)))
lues = sum(1 for r in roster if r["reco"] and r["recoOf"] == r["name"])
her = sum(1 for r in roster if r["reco"] and r["recoOf"] != r["name"])
print("stats recommandees par le jeu : %d entrees sur %d (%d lues sur leur fiche, "
      "%d heritees de la base)" % (lues + her, len(roster), lues, her))
print("en attente d'une fiche complete (%d) :" % len(attente))
for r in attente:
    print("   %-10s No.%-6s manque : %s" % (r["name"], r["no"], ", ".join(r["manque"])))
