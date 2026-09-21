# -*- coding: utf-8 -*-
"""Compare les deux sources et ecrit raw/_audit.json.

Rien n'est corrige ici, et surtout rien n'est arbitre : quand Game8 et aniidex
ne disent pas la meme chose, les deux valeurs sont conservees cote a cote. Le
fichier produit est la liste de ce qu'il reste a verifier dans le jeu, et c'est
lui que la surveillance quotidienne relit pour savoir ce qui a bouge.

    python audit.py
"""
import io, json, collections

G = {r["name"]: r for r in json.load(io.open("raw/parsed.json", encoding="utf-8"))}
GB = {n: r for n, r in G.items() if r["kind"] == "base"}
try:
    A = {r["name"]: r for r in json.load(io.open("raw/parsed_aniidex.json", encoding="utf-8"))}
except IOError:
    A = {}

rep = collections.OrderedDict()

# --- 1. couverture -------------------------------------------------------
rep["absents_de_game8"] = sorted(set(A) - set(GB))
rep["absents_d_aniidex"] = sorted(set(GB) - set(A))
rep["bases_communes"] = len(set(A) & set(GB))

# --- 2. fiches incompletes ----------------------------------------------
# Un Aniimo annonce mais dont le jeu n'a pas encore publie le role ou les stats
# ne peut pas etre classe. On le nomme au lieu de lui inventer une valeur.
inc = {}
for n, r in list(A.items()) + list(GB.items()):
    manque = [k for k in ("role", "el", "skills") if not r.get(k)]
    if not r.get("stats") or any(v in (0, None) for v in r["stats"].values()):
        manque.append("stats")
    if manque:
        inc.setdefault(n, sorted(set(manque)))
rep["fiches_incompletes"] = inc

# --- 3. divergences sur les bases communes ------------------------------
div = collections.OrderedDict()
for n in sorted(set(A) & set(GB)):
    a, g = A[n], GB[n]
    d = {}
    if a["stats"] != g["stats"]:
        d["stats"] = {"game8": g["stats"], "aniidex": a["stats"]}
    if sorted(a["el"]) != sorted(g["el"]):
        d["elements"] = {"game8": g["el"], "aniidex": a["el"]}
    if a["role"] and g["role"] and a["role"] != g["role"]:
        d["role"] = {"game8": g["role"], "aniidex": a["role"]}
    sa = set(s["n"] for s in a["skills"])
    sg = set(s["n"] for s in g["skills"])
    if sa != sg:
        # Game8 regroupe sur la fiche de base les competences de toutes ses
        # formes ; aniidex separe forme par forme. Un simple sous-ensemble est
        # donc attendu et n'est pas signale comme desaccord.
        d["competences"] = {"game8_seul": sorted(sg - sa), "aniidex_seul": sorted(sa - sg),
                            "sous_ensemble": sa < sg}
    if d:
        div[n] = d
rep["divergences"] = div
rep["compte_divergences"] = {
    k: sum(1 for d in div.values() if k in d)
    for k in ("stats", "elements", "role", "competences")}
rep["desaccords_vrais"] = sorted(
    n for n, d in div.items()
    if "stats" in d or "elements" in d or "role" in d
    or (("competences" in d) and not d["competences"]["sous_ensemble"]))

# --- 4. ce qu'aniidex apporte et que Game8 n'a pas ----------------------
rep["apports_aniidex"] = {
    "competences_chiffrees": sum(1 for r in A.values() for s in r["skills"] if "mi" in s),
    "ameliorations_eveil": sum(len(r.get("upgrades") or []) for r in A.values()),
    "formes_annoncees": sorted({"%s (%s)" % (n, f[0]) for n, r in A.items()
                                for f in r.get("forms") or []
                                if "%s %s" % (f[0], n) not in G}),
}

io.open("raw/_audit.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps(rep, ensure_ascii=False, indent=1))

print("bases communes %d | absents de Game8 %d | absents d'aniidex %d"
      % (rep["bases_communes"], len(rep["absents_de_game8"]), len(rep["absents_d_aniidex"])))
print("absents de Game8 :", ", ".join(rep["absents_de_game8"]))
print("fiches incompletes (%d) :" % len(inc))
for n in sorted(inc):
    print("   %-12s manque : %s" % (n, ", ".join(inc[n])))
print("divergences :", rep["compte_divergences"])
print("desaccords a trancher dans le jeu (%d) : %s"
      % (len(rep["desaccords_vrais"]), ", ".join(rep["desaccords_vrais"])))
print("apports aniidex :", rep["apports_aniidex"]["competences_chiffrees"],
      "competences chiffrees,", rep["apports_aniidex"]["ameliorations_eveil"], "ameliorations,",
      len(rep["apports_aniidex"]["formes_annoncees"]), "formes non couvertes")
