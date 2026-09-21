# -*- coding: utf-8 -*-
"""Tier lists externes, relevees le 18/09/2026, utilisees UNIQUEMENT pour valider
le modele et mesurer la confiance - jamais comme entree du score.

Sources independantes retenues. Ecartees : showgamer.com et gamezebo.com (copies
quasi exactes de Game8), progameguides.com (403), games.gg (liste tronquee).
Sortie : raw/_ext_tiers.json  {source: {nom_roster: position 0..1 (1 = meilleur)}}

Les noms qu'une source cite et que le roster ne connait pas sont conserves dans
la sortie (champ hors_roster) au lieu d'etre oublies : c'est ce silence qui
avait cache douze Aniimo reels (No. 084 et au-dela) que Game8 n'a pas encore
rediges. Un nom hors roster est soit un Aniimo qui nous manque, soit un nom
qu'une source a invente - dans les deux cas, il faut le voir.
"""
import io, json, re, difflib

SRC = {
 "game8": ("game8.co/games/Aniimo/archives/621098", ["S", "A", "B", "C", "D"], None),  # lu dans raw/_tier_game8.json
 "aniimoguide": ("aniimoguide.com/tier-list", ["T0", "T0.5", "T1", "T1.5", "T2", "T2.5", "T3"], """
T0: Irisalis, Fulmintis, Helion, Lunara, Rookey, Besauce, Somniwing
T0.5: Scorchhowl, Thornblade, Pawney, Panpanta, Helgon, Inferlupa, Minespine, Blazen, Tromber, Dazmand, Fragrancier, Melloblum, Hexxin, Glacy, Gracewing
T1: Waleetle, Cornet, Ignitis, Infergon, Geoclaw, Tubster, Magmarex, Piopiota, Turbo, Luminelle, Bailite, Eklue, Erlath, Leafy
T1.5: Grizbo, Stellarys
T2: Glynsera, Sherro, Fenmane, Irisal, Sheldon, Flameruff, Fenrier, Baleetle, Cubbo, Shrubclaw, Tuckin, Pomawk, Helmwhelp, Geodeback, Lavazar, Popota, Hummin, Dreaple, Bouldus, Veilfloat, Chirpi, Nimbi, Bolty, Cozite, Dewy, Flamerion, Fahloo
T2.5: Celestis, Fentuft, Budsquire, Wisptis, Pomegg, Budclaw, Pranky, Flutternym, Sparki
T3: Iris, Emberpup, Shelly, Bonesky, Susuta, Jawling, Pebbling, Helmut, Skippy, Eko, Bulbly
"""),
 "mobi": ("mobi.gg/en/tips/aniimo-tier-list", ["S+", "S", "A", "B"], """
S+: Glacy (Prismana Form), Coraliz, Fulmintis (Prismana Form), Stellarys (Umbrabow Form), Glynsera (Prismana Form), Lunara, Pawney (Prismana Form), Scorchhowl (Umbrabow Form), Glynsera, Magmarex (Prismana Form), Thornblade (Umbrabow Form), Geoclaw, Stellarys (Prismana Form), Infergon, Inferlupa, Leafy, Luminelle (Prismana Form), Gracewing, Minespine, Waleetle (Highland Form), Grizbo (Prismana Form)
S: Magmarex (Umbrabow Form), Glameep, Helion, Fulmintis, Ignitis (Highland Form), Sherro (Thunderstorm Form), Glynsera (Highland Form), Witchin (Umbrabow Form), Coraliz (Highland Form), Luminelle (Rainstorm Form), Sherro (Prismana Form), Pawney, Witchin (Prismana Form), Pomawk (Thunderstorm Form), Turbo (Umbrabow Form), Irisalis, Blazen (Prismana Form), Fenmane, Magmarex, Pawney (Highland Form), Scorchhowl (Thunderstorm Form), Melloblum, Piopiota, Gracewing (Highland Form), Gracewing (Mountain Woods Form), Sherro, Sherro (Umbrabow Form), Susuta, Thornblade (Rainstorm Form), Stellarys, Fenmane (Prismana Form), Panpanta (Prismana Form), Pawney (Umbrabow Form), Glacy, Pawney (Mountain Woods Form), Pomegg, Thornblade, Erlath, Flameruff (Mountain Woods Form), Thornblade (Highland Form), Cubbo, Flutternym (Highland Form), Turbo (Highland Form), Turbo (Mountain Woods Form), Turbo (Thunderstorm Form), Blazen (Highland Form), Flameruff, Gachapus, Malevsera, Glacy (Mountain Woods Form), Gracewing (Thunderstorm Form), Ignitis, Ignitis (Prismana Form), Pomawk (Highland Form), Stellarys (Rainstorm Form), Bouldus (Highland Form), Ignitis (Mountain Woods Form), Piopiota (Highland Form), Dazmand, Celestis, Scorchhowl (Prismana Form), Helmut, Popapus, Besauce, Ignitis (Umbrabow Form), Panpanta (Highland Form), Wisptis (Highland Form), Wavwal
A: Dreaple, Tromber, Tromber (Mountain Woods Form), Emberpup, Emberpup (Mountain Woods Form), Iris, Nimbi (Highland Form), Fenrier, Fenrier (Highland Form), Luminelle, Panpanta, Scorchhowl, Cornet (Prismana Form), Flutternym, Hummin (Highland Form), Wisptis, Wisptis (Mountain Woods Form), Susuta (Highland Form), Tromber (Highland Form), Bailite, Fahloo, Iris (Highland Form), Iris (Thunderstorm Form), Nimbi, Blazen, Flamerion, Baleetle, Bonesky, Bonesky (Highland Form), Cornet, Cornet (Mountain Woods Form), Cornet (Umbrabow Form), Flutternym (Mountain Woods Form), Perfumer, Shelly, Waleetle, Bolty, Flameruff (Highland Form), Iris (Mountain Woods Form), Iris (Mudflat Form), Irisal (Rainstorm Form), Pomawk, Popota (Highland Form), Witchin, Witchin (Highland Form)
B: Bouldus, Eklue, Chirpi (Mountain Woods Form), Baleetle (Highland Form), Chirpi, Tubster (Mountain Woods Form), Scorchhowl (Highland Form), Scorchhowl (Mountain Woods Form), Bolty (Highland Form), Emberpup (Highland Form), Flutternym (Thunderstorm Form), Iris (Rainstorm Form), Irisal, Turbo, Budsquire, Tubster (Highland Form), Popota, Sheldon, Tubster
"""),
 "allthings": ("allthings.how/aniimo-release-meta-tier-list", ["S", "A", "B", "C", "D"], """
S: Irisalis, Eklue, Gracewing, Coraliz, Wavwal
A: Inferlupa, Tromber, Tubster, Glacy, Leafy, Somniwing, Tuckin, Geoclaw, Melloblum, Fulmintis, Rookey, Grizbo, Luminelle, Glameep, Malevsera, Lunara, Fennelun, Helion, Soleon
B: Scorchhowl, Stellarys, Cornet, Irisal, Turbo, Dreaple, Witchin, Shrubclaw, Thornblade, Dazmand, Pomawk, Ignitis, Glynsera, Blazen, Piopiota, Panpanta, Sherro, Waleetle, Pawney, Helgon, Infergon, Magmarex, Minespine, Besauce, Erlath, Gachapus
C: Flamerion, Fragrancier, Bouldus, Fenmane, Bailite, Bubbeep
D: Popapus
"""),
 "kongbakpao": ("kongbakpao.com/aniimo-tier-list", ["SS", "S", "A", "B", "C", "D"], """
SS: Helion, Lunara, Pawney (Prismana Form), Fulmintis (Prismana Form), Stellarys (Prismana Form), Inferlupa, Glacy (Prismana Form), Glacy (Sea of Flowers Form), Glynsera (Prismana Form), Irisalis, Somniwing, Gracewing, Magmarex (Prismana Form), Panpanta (Prismana Form), Glameep (Prismana Form), Scorchhowl (Prismana Form), Pawney (Snowfield Form), Thornblade (Prismana Form), Witchin (Prismana Form), Blazen (Prismana Form), Grizbo (Prismana Form), Luminelle (Prismana Form), Pawney, Sherro (Prismana Form), Sherro (Thunderstorm Form), Sherro, Glacy, Glacy (Snowfield Form), Luminelle (Rainstorm Form), Celestis, Ignitis (Highland Form), Leafy, Witching (Umbrabow Form), Thornblade (Rainstorm Form), Gracewing (Nighttime Form), Pawny (Mountain Form), Susuta, Scorchhowl (Thunderstorm Form)
S: Thornblade, Iris, Magmarex, Fenmane (Prismana Form), Gracewing (Sea of Flowers Form), Glynsera (Nighttime Form), Glynsera, Infergon, Fulmintis, Gachapus, Popapus, Melloblum, Erlath, Flutternym (Sea of Flowers Form), Sparkelf, Malevsera, Coraliz, Coraliz (Rainstorm Form), Glameep, Stellarys, Ignitis, Ignitis (Forest Form), Minespine, Blazen (Mountain Form), Grizbo, Fenmane, Melloblum (Prismana Form), Turbo (Prismana Form), Dreaple, Geoclaw, Fragancier, Panpanta, Irisal, Pomawk (Snowfield Form), Emberpup (Mountain Form), Stellarys (Rainstorm Form), Ignitis (Prismana Form), Flameruff (Mountain Form), Thornblade (Towerwood Form), Skippy (Sea of Flowers Form)
A: Cubbo, Reefish, Piopiota, Budclaw, Waleetle (Snowfield Form), Cornet (Prismana Form), Rookey (Snowfield Form), Besauce, Eklue, Emberpup, Susuta (Nighttime Form), Pnapanta (Nighttime Form), Bonesky (Nighttime Form), Iris (Plateau Form), Fenrier, Flutternym, Dazmand, Cornet (Highland Form), Budclaw (Mudflat Form), Irisal (Prismana Form), Pranky (Sea of Flowers Form), Shrubclaw (Mudflat Form), Iris (Highland Form), Iris (Prismana Form), Reefish (Rainstorm Form), Turbo (Cloudmist Form), Turbo (Rainstorm Form), Fenrier (Nighttime Form), Nimbi (Rainstorm Form), Pomawk, Boldus (Snowfield Form), Wisptis (Forest Form), Flutternym (Nighttime Form), Flutternym (Mountain Form), Gracewing (Mountain Form), Irisal (Mountain Form), Rookey (Mountain Form), Irisal (Forest Form), Nimbi, Skippy (Snowfield Form), Flamerion (Sea of Flowers Form), Turbo (Plateau Form), Baleetle (Snowfield Form), Scorchhowl (Highland Form), Helgon, Helgon (Mountain Form), Emberpup (Highland Form), Scorchhowl, Scorchhowl (Mountain Form), Blazen, Bonesky, Pebbling, Pranky, Waleetle (Prismana Form)
B: Bybbeep, Budsquire (Towerwood Form), Eko, Flamerion (Highland Form), Irisal (Highland Form), Malangel, Shrubclaw (Beach Form), Shelly, Pomegg, Helmut, Pomawk (Sea of Flowers Form), Pomegg (Sea of Flowers Form), Sparkelf (Prismana Form), Chiripi (Highland Form), Cheekie, Flameruff, Iris (Forest Form), Lavazer, Skippy, Tromber, Tromber (Beach Form), Wisptis, Witchin, Piopiota (Nighttime Form), Tromber (Highland Form), Wavwal, Rookey, Sheldon, Dewy, Bulbly, Veilfloat, Luminelle, Fentuft, Geodeback, Helmut (Snowfield Form), Helmut (Mountain Form), Helmwhelp, Helmwhelp (Mountain Form), Pomawk (Highland Form), Pomegg (Snowfield Form), Infergon (Prismana Form), Nimbi (Plateau Form), Sparki, Budclaw (ALT Form), Inferlupa (Prismana Form)
C: Pomegg (Highland Form), Sparki (Forest Form), Sparki (Sea of Flowers Form), Shrubclaw (Bay Form), Cozite, Tubster, Fahloo, Hummin (Mountain Form), Baleetle, Waleetle, Bolty (Mountain Woods Form), Chirpi (Beach Form), Cornet (Beach Form), Squashel
D: Tubster (Beach Form), Tubster (Highland Form), Chirpi, Cornet, Bailite, Squarrel
"""),
 "powerup": ("powerupgaming.co.uk/2026/09/16/aniimo-tier-list-best-aniimo-ranked-by-role", ["S", "A", "B", "C", "D"], """
S: Irisal, Somniwing, Rookey, Besauce, Helion, Lunara, Stellarys, Malevsera
A: Grizbo, Fenmane, Fulmintis, Coraliz, Glacy, Wavwal, Geoclaw, Gracewing
B: Magmarex, Infergon, Inferlupa, Leafy, Waleetle, Panpanta, Sherro
C: Nimbi, Pomegg, Cubbo, Flameruff, Baleetle, Bolty
D: Iris, Shelly, Helmut, Bonesky, Emberpup, Skippy
"""),
}

D = json.load(io.open("raw/parsed.json", encoding="utf-8"))
ROSTER = {r["name"] for r in D}
REGIONS = sorted({r["name"].rsplit(" ", 1)[0] for r in D if r["kind"] == "form"}, key=len)


def canon(label):
    """'Pawney (Prismana Form)' -> 'Prismana Pawney' ; fautes de frappe corrigees
    par rapprochement avec le roster (ratio >= 0.85), sinon None (hors roster)."""
    label = label.strip()
    m = re.match(r"(.+?) \((.+?) Form\)$", label)
    name = ("%s %s" % (m.group(2), m.group(1))) if m else label
    if name in ROSTER:
        return name
    close = difflib.get_close_matches(name, ROSTER, n=1, cutoff=0.85)
    return close[0] if close else None


out, dropped = {}, {}
g8 = json.load(io.open("raw/_tier_game8.json", encoding="utf-8"))
for src, (url, levels, text) in SRC.items():
    pos = {}
    if text is None:
        tiers = g8
    else:
        tiers = {}
        for line in text.strip().splitlines():
            t, names = line.split(":", 1)
            tiers[t.strip()] = [x for x in names.split(",") if x.strip()]
    for i, lv in enumerate(levels):
        for lab in tiers.get(lv, []):
            n = canon(lab)
            if n is None:
                dropped.setdefault(src, []).append(lab.strip())
                continue
            # position 0..1 : haut de l'echelle = 1. Echelles de longueurs differentes
            # ramenees au meme intervalle ; la comparaison se fait ensuite en rangs.
            pos.setdefault(n, 1 - i / (len(levels) - 1))
    out[src] = {"url": url, "levels": levels, "pos": pos,
                "hors_roster": sorted(set(dropped.get(src, [])))}

io.open("raw/_ext_tiers.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
for s, v in sorted(out.items()):
    print("%-11s %3d entrees du roster | %2d hors roster" % (s, len(v["pos"]), len(v["hors_roster"])))

# Un nom cite par plusieurs sources independantes et absent du roster n'est plus
# une faute de frappe : c'est un Aniimo a aller chercher.
import collections
c = collections.Counter(n for v in out.values() for n in v["hors_roster"])
multi = sorted(n for n, k in c.items() if k >= 2)
print("hors roster cites par au moins deux sources (%d) : %s" % (len(multi), ", ".join(multi)))
