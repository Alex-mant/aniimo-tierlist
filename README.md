# Aniimo — Tier List

Site statique local, sans dépendance ni CDN. Classement recalculé de zéro à partir des
fiches du jeu : aucune tier list existante n'est reprise comme source.

## Lancer

```bash
cd /d/REPOS/amo
python -m http.server 8777 --bind 127.0.0.1
```

→ **http://127.0.0.1:8777/**

## Chaîne de traitement

```
raw/*.html  ──parse.py──>  raw/parsed.json  ──score.py──>  data.js  ──>  index.html
 219 pages                   207 fiches        ▲             207 entrées
                                               │
                             kits.json (116 lectures) + synergy.json + raw/_kitmap.json
                                               + raw/_tier_game8.json
```

| Fichier | Rôle |
|---|---|
| `raw/` | Pages sources scrapées (47 Mo). Ne pas re-télécharger, c'est la vérité terrain. |
| `parse.py` | HTML → JSON : stats, traits, compétences, formes, mobilité. |
| `RUBRIC.md` | La grille de notation des kits, écrite **avant** la lecture. |
| `kits/b1..b6.json` | Les 116 kits notés, par lots de 20 — la trace de la lecture. |
| `kits.json` | Fusion des six lots, source unique consommée par `score.py`. |
| `synergy.json` | Verrous élémentaires et duos nommés, pour le constructeur d'équipe. |
| `score.py` | JSON → `data.js` : scoring, synergies, paliers. |
| `index.html` | L'app (HTML/CSS/JS vanilla, un seul fichier). |
| `images/` | 207 icônes Game8 (190×190), une par entrée classée — une seule source pour un rendu homogène. |
| `_index_v1.html.bak`, `_index_v2_112.html.bak`, `_score_v1.py.bak` | Versions précédentes. |

Régénérer : `python parse.py && python score.py`

## Modèle

`score = (0,50 × stats + 0,32 × kit + 0,18 × synergie) × multiplicateur de stade`

Tous les curseurs d'investissement sont poussés au maximum jouable. Comme le plafond
(niveau, Résonance, potentiel, Points et Fruit de Capacité, Rangs d'Attribut) est
**identique pour tous les Aniimo**, le classement se joue sur ce qui diffère réellement :
stats de base, marge de croissance des stats couronnables (×24/20 sur les deux stats
favorables du rôle) et kit.

### Le kit : 116 lectures à la main

Le point qui sépare ce classement d'une extraction automatique. Les 116 kits distincts du
roster ont été lus un par un — traits, compétences innées, compétences de combat, ultime —
puis notés de 0 à 10 sur six axes selon la grille fixe de `RUBRIC.md` : `dmg`, `team`,
`brk`, `sust`, `res`, `ctrl`. S'y ajoute une conditionnalité de 0 à 3, qui retire 6 % du
score de kit par palier.

Les notes sont **absolues**, pas relatives au roster : elles ne bougent pas si le roster
change. Les 91 formes régionales qui réutilisent le kit de leur base en héritent via
`raw/_kitmap.json`.

## Les trois rosters, une seule tier list

Le classement est **unique** : les 207 entrées sont découpées sur la même échelle et
affichées dans une seule tier list. C'est le but recherché qui l'impose — on compose une
équipe de quatre, et un Normal, une forme régionale et une Prismana se recrutent dans le
même vivier. Des classements séparés compareraient chacun à ses semblables au lieu de ses
concurrents réels ; une Prismana pouvait alors se retrouver classée sous sa propre base à
score égal.

Les trois puces du bandeau sont donc des **filtres cumulables** : elles retirent ou
remettent un groupe dans le classement (« sans les Prismana », « Normaux seuls »…), elles ne
le découpent pas. Le bouton **Tous** remet tout. Chaque version reste une entrée à part
entière :

- **Normaux** — 88 Aniimo de base.
- **Formes régionales** — 95 variantes. **40** d'entre elles sont strictement identiques à
  leur base sur tout ce qui est mesuré (stats, kit, éléments, rôle) : elles portent un `=`
  et le filtre « Masquer les formes identiques » les retire.
- **Prismana** — 24 formes, avec leurs stats et leurs kits propres. **5** portent aussi le
  `=` : Prismana Panpanta, Hexxin, Pawney, Irisal et Iris ont exactement la fiche de leur
  base, la forme Prismana n'y apporte rien de mesurable.

## L'échelle des paliers

Les paliers sont des percentiles (10 / 25 / 52 / 80 %) découpés sur le vivier affiché : une
position relative, pas une puissance absolue. Sans filtre, la découpe porte sur les 207
entrées et donne S 21 · A 31 · B 56 · C 58 · D 41. Les Prismana y remontent d'elles-mêmes
(**S 4 · A 7 · B 10 · C 2 · D 1**), ce qui est attendu : ce sont des versions améliorées
d'Aniimo déjà corrects, leur médiane est plus haute que celle du roster de base.

Restreindre le vivier avec un filtre le redécoupe — un palier répond toujours à la question
« où se situe cet Aniimo *parmi ceux qui sont affichés* ». Le score, lui, ne bouge pas.

## Vues

| Vue | Contenu |
|---|---|
| **Tiers** | Tier list S→D, paliers recalculés selon les filtres actifs |
| **Stats** | Tableau triable : stats de base, score, ses trois composantes, palier Game8 |
| **Équipe** | Constructeur d'équipe avec note de synergie |
| **Réglages** | Poids modifiables en direct, test de stabilité, accord avec Game8 |
| **Méthode** | Le modèle complet et les limites connues |

Filtres : roster, rôle, élément (9), stade, masquer les formes identiques, recherche.
Clic sur une carte → fiche détaillée : décomposition du score, lecture du kit sur les six
axes, verrou élémentaire éventuel, synergie, traits et compétences.

## Constructeur d'équipe

Note sur 100 croisant cinq termes : puissance individuelle (30 %), couverture des six axes
de kit (30 %), éléments (12 %), rôles (13 %), combos (15 %), moins les manques structurels.
Sur un axe, c'est le meilleur porteur qui compte plus 40 % du second — la redondance aide
sans doubler l'effet.

Les combos viennent de `synergy.json`, tiré de la lecture des kits, pas d'une heuristique :

- **26 verrous élémentaires** — kits dont l'apport collectif ne vaut que pour des alliés
  d'un élément donné (buff réservé, ou réduction de résistance). Ils rapportent des points
  si des alliés portent cet élément, et en font perdre si personne ne le porte.
- **5 dépendances nommées** — lues explicitement : Iris qui amplifie sur du Gazon que seul
  Leafy sait créer, Bouldus dont la conversion de Rochers exige Waleetle, le +30 % de BREAK
  de la famille Susuta qui réclame un Susuta du sexe opposé, le relais d'EP de la famille
  Chirpi, Melloblum et son +70 % de critique Herbe sans porteur Herbe.
- **4 manques structurels** retirent directement des points : aucune source d'EP, aucun
  BREAK, aucune survie, ou un Pawney sans briseur.

Le bouton **Composer automatiquement** fait une recherche gloutonne sur le vivier filtré.

## Poids réglables et stabilité

La vue Réglages rend modifiables le mélange stats/kit/synergie, les poids de stats par
rôle, les poids d'axes de kit par rôle et les poids d'apport collectif. Tout se recalcule
côté client : `statParts` et `axes` sont exportés bruts dans `data.js`, donc le score entier
est reconstructible sans repasser par Python.

Le **test de stabilité** tire 200 jeux de poids perturbés de ±25 % et compte combien de fois
chaque Aniimo retombe dans le même palier. Aux poids de référence, le tirage étant aléatoire :
**200 à 202 sur 207** gardent leur palier dans au moins 60 % des tirages, moyenne 89 %. Les
autres portent un `~` dans la tier list — leur place tient au réglage, pas à leur fiche. Ce
sont toujours les mêmes : Highland Pomawk, Sea of Flowers Pomawk, Fenmane, Rookey, Fentuft,
Plateau Turbo, Prismana Infergon (53 à 59 %).

## Recoupement avec le consensus

Le classement n'est pas calé sur les tier lists publiées, mais il leur est comparé pour
repérer où il s'en écarte. Sur les **84** Aniimo que Game8 classe : **33 %** de paliers
identiques, **76 %** à un palier près, corrélation des rangs **0,54**. Les chiffres se
recalculent en direct quand on bouge un curseur.

Les écarts ne sont pas des erreurs à corriger. Le motif dominant est net : les tier lists
communautaires notent plus haut les DPS à burst conditionnel et plus bas les Break et
Support à grosses stats. C'est cohérent — elles jugent la facilité de jeu réelle, ce modèle
juge le plafond à investissement maximal.

## Limites connues

- **P.Déf est une valeur dérivée.** Le tableau source duplique l'Attaque dans la cellule
  P.Déf — vérifié sur les 207 pages, sans une seule exception. Le Total de base étant
  correct, P.Déf est reconstruit par soustraction.
- **Lunara** affiche ATQ 64 / P.Déf 116 pour un DPS. Les deux ordres donnent le même Total
  de 514, donc la source ne permet pas de trancher ; la cellule Attaque faisant foi partout
  ailleurs, la valeur est conservée telle quelle et signalée dans sa fiche. C'est la plus
  forte divergence avec Game8, qui le classe S.
- **Soleon** (N° 9999) affiche `??` partout dans la source : non sorti, donc exclu.
- Le modèle ne mesure ni la vitesse d'animation, ni la portée, ni le confort de jeu.
- Les paliers sont des percentiles : une position relative dans le vivier affiché, pas une
  puissance absolue. Changer un filtre les recalcule.

## Tests

Harnais jsdom (le site n'a pas de dépendance, le test si) :

```bash
cd <scratchpad>/ && node smoke.js
```

51 assertions : conformité du recalcul client au `score.py` de référence, comptages par
tier list unique, non-inversion des Prismana, puces de roster cumulables, badges `=`,
filtres, modale, tri du tableau, constructeur d'équipe de bout en bout, curseurs de poids,
calibration, test de stabilité.
