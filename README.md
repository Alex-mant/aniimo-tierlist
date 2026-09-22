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
                fetch.py  (le seul accès réseau du dépôt)
                   │
      ┌─────────┴──────────┬───────────────┐
 raw/*.html            raw_aniidex/*.html   images/*.png
 220 pages (Game8)     100 fiches (aniidex.com)
      │                     │
  parse.py            parse_aniidex.py
      │                     │
 raw/parsed.json      raw/parsed_aniidex.json  ──audit.py──>  raw/_audit.json
      │                     │
      └─────────┬─────────┘
             merge.py  ──>  raw/roster.json     215 entrées classables
                │        ──>  raw/_attente.json    6 annoncées, non classables
                │
   score.py  ──>  data.js  ──>  index.html  ──>  smoke.js (89 assertions)
      ▲
      │
 kits.json (122 lectures) + kit_skills.json + synergy.json
 + raw/_kitmap.json + raw/_ext_tiers.json (6 tier lists)
```

| Fichier | Rôle |
|---|---|
| `fetch.py` | Le seul fichier qui touche au réseau. Relève les deux sources, dit ce qui a bougé. |
| `raw/` | Pages Game8 scrapées (47 Mo). Ne pas re-télécharger sans raison : c'est la vérité terrain. |
| `raw_aniidex/` | Fiches aniidex.com (19 Mo), seconde source indépendante. |
| `parse_aniidex.py` | HTML aniidex → `raw/parsed_aniidex.json`, même schéma que `parse.py`, plus les deux statistiques recommandées par le jeu (57 fiches). |
| `audit.py` | Confronte les deux sources → `raw/_audit.json`. N'arbitre rien, signale tout. |
| `merge.py` | Assemble le roster classable des deux sources → `raw/roster.json` + `raw/_attente.json`, et reporte les statistiques recommandées sur les formes de la même espèce. |
| `parse.py` | HTML → JSON : stats, traits, compétences, formes, mobilité. |
| `RUBRIC.md` | La grille de notation des kits, écrite **avant** la lecture. |
| `kits/b1..b7.json` | Les 122 kits notés, par lots — la trace de la lecture. |
| `kits.json` | Fusion des sept lots, source unique consommée par `score.py`. |
| `kit_skills.json` | Ce que porte **chaque compétence** sur les six axes (0..3). Voir plus bas. |
| `ext_tiers.py` | Relève les 6 tier lists publiées → `raw/_ext_tiers.json`, pour recoupement. |
| `synergy.json` | Verrous élémentaires et duos nommés, pour le constructeur d'équipe. |
| `score.py` | JSON → `data.js` : scoring, synergies, paliers. |
| `index.html` | L'app (HTML/CSS/JS vanilla, un seul fichier). |
| `smoke.js` | Banc d'essai jsdom : charge la page, clique, vérifie ce qu'elle affiche. `npm test`. |
| `images/` | 215 icônes (190×190), une par entrée classée — une seule source pour un rendu homogène. |
| `_index_v1.html.bak`, `_index_v2_112.html.bak`, `_score_v1.py.bak` | Versions précédentes. |

Régénérer : `python parse.py && python parse_aniidex.py && python merge.py && python score.py`

`merge.py` est le seul endroit où les deux sources se rejoignent, et sa règle tient en une
phrase : **aniidex n'écrase jamais Game8, il ne fait qu'ajouter**. Un Aniimo que Game8 n'a
pas encore rédigé entre dans le roster si et seulement si la seconde source lui donne les
quatre choses sans lesquelles on ne peut rien classer — rôle, élément, compétences, stats.
Sinon il part dans `raw/_attente.json`, nommé avec ce qui lui manque, et la page l'affiche
tel quel. Rien n'y est deviné.

## Modèle

`score = (0,50 × stats + 0,32 × kit + 0,18 × synergie) × multiplicateur de stade`

Tous les curseurs d'investissement sont poussés au maximum jouable : la tier list juge
l'**exemplaire parfait**, jamais celui qu'on vient d'attraper.

### Le hasard de la capture, et pourquoi il ne classe rien

Deux exemplaires d'un même Aniimo n'ont pas les mêmes statistiques. Le jeu tire à la capture
un **potentiel inné** par statistique — l'expertise le note Commun 66 % · Bon 26 % ·
Élite 7,2 % · Parfait 0,8 % — puis l'Éveil d'aptitude laisse monter ce potentiel contre de la
Poussière d'étoile. Inné et acquis partagent le même plafond :

| | plafond | croissance de la stat |
|---|---|---|
| statistique ordinaire | 20 points | ×1,80 |
| statistique recommandée par le jeu, après Ascension de résident | 24 points | ×1,96 |

Chaque point vaut **+4 %** de la statistique (et +6 PC). Le plafond étant le même pour tous,
le tirage ne classe rien : il dit seulement combien de Poussière d'étoile il faudra. Ce qui
classe, c'est la stat de base **poussée à ce plafond**, puis le kit.

L'avantage d'une statistique couronnée est donc de **+8,9 %** (1,96 / 1,80), et non les
+20 % que suggère le rapport 24/20 — c'est la correction de fond apportée à cette version, et
elle ne déplace que 4 entrées sur 215, ce qui en dit long sur la robustesse du reste.

**Quelles statistiques sont couronnables ?** Le jeu le dit **par Aniimo, pas par rôle** : c'est
le pouce vert de l'hexagone, celui que porte l'icône couronne et auquel le Capafruit ajoute son
point. aniidex le publie pour 57 fiches, ce qui couvre **128 entrées sur 215** une fois reporté
aux formes régionales et Prismana de la même espèce. Pour les 87 restantes, on retombe sur les
deux statistiques que le jeu recommande le plus souvent *dans le même rôle*, comptées sur les
fiches où il les a réellement publiées — DPS ATQ+RÉG, Break BREAK+DÉF.P, Support ATQ+PV,
Regen PV+RÉG, Heal PV+RÉG. C'est un défaut **mesuré**, pas supposé, et la fiche de chaque
Aniimo dit laquelle des deux situations s'applique. La version précédente devinait ces deux
stats par rôle : le jeu lui donnait raison 7 fois sur 57.

### La personnalité, deuxième tirage

Le jeu tire aussi une **personnalité** à la capture (16 types, quatre créneaux de deux
lettres) — E Énergique ATQ +2 %/BREAK +2 % ou I Instinctif RÉGEN +4 % ; S Pratique dégâts
+4 % ou N Agile critique +5 % ; T Tenace DÉF.P +6 % ou F Fidèle DÉF.M +6 % ; J Judicieux
PV +4 % ou P Joueur réduction de dégâts +4 %. Elle se rejoue au Fruit de psyché : sur
l'exemplaire parfait c'est donc un **choix**, pas un tirage.

Elle n'entre volontairement **pas** dans le calcul, et la raison est arithmétique : le
meilleur choix est le même pour tous les Aniimo d'un rôle, or la note de stat est normalisée
par rôle — un bonus uniforme s'y annulerait exactement. Deux de ses quatre créneaux ne
touchent d'ailleurs même pas une statistique (dégâts, critique, réduction). Elle est publiée
sur chaque fiche parce qu'elle fait partie de la forme parfaite à viser.

### Le kit : 122 lectures à la main

Le point qui sépare ce classement d'une extraction automatique. Les 122 kits distincts du
roster ont été lus un par un — traits, compétences innées, compétences de combat, ultime —
puis notés de 0 à 10 sur six axes selon la grille fixe de `RUBRIC.md` : `dmg`, `team`,
`brk`, `sust`, `res`, `ctrl`. S'y ajoute une conditionnalité de 0 à 3, qui retire 6 % du
score de kit par palier.

Les notes sont **absolues**, pas relatives au roster : elles ne bougent pas si le roster
change. Les 93 formes régionales qui réutilisent le kit de leur base en héritent via
`raw/_kitmap.json`.

## Les trois rosters, une seule tier list

Le classement est **unique** : les 215 entrées sont découpées sur la même échelle et
affichées dans une seule tier list. C'est le but recherché qui l'impose — on compose une
équipe de quatre, et un Normal, une forme régionale et une Prismana se recrutent dans le
même vivier. Des classements séparés compareraient chacun à ses semblables au lieu de ses
concurrents réels ; une Prismana pouvait alors se retrouver classée sous sa propre base à
score égal.

Les trois puces du bandeau sont donc des **filtres cumulables** : elles retirent ou
remettent un groupe dans le classement (« sans les Prismana », « Normaux seuls »…), elles ne
le découpent pas. Le bouton **Tous** remet tout. Chaque version reste une entrée à part
entière :

- **Normaux** — 94 Aniimo de base.
- **Formes régionales** — 97 variantes. **40** d'entre elles sont strictement identiques à
  leur base sur tout ce qui est mesuré (stats, kit, éléments, rôle) : elles portent un `=`
  et le filtre « Masquer les formes identiques » les retire.
- **Prismana** — 24 formes, avec leurs stats et leurs kits propres. **5** portent aussi le
  `=` : Prismana Panpanta, Hexxin, Pawney, Irisal et Iris ont exactement la fiche de leur
  base, la forme Prismana n'y apporte rien de mesurable.

## L'échelle des paliers

Les paliers sont des percentiles (10 / 25 / 52 / 80 %) découpés sur le vivier affiché : une
position relative, pas une puissance absolue. Sans filtre, la découpe porte sur les 215
entrées et donne S 23 · A 31 · B 58 · C 60 · D 43. Les Prismana y remontent d'elles-mêmes
(**S 10 · A 5 · B 8 · C 0 · D 1**), ce qui est attendu : ce sont des versions améliorées
d'Aniimo déjà corrects, leur médiane est plus haute que celle du roster de base.

Restreindre le vivier avec un filtre le redécoupe — un palier répond toujours à la question
« où se situe cet Aniimo *parmi ceux qui sont affichés* ». Le score, lui, ne bouge pas.

## Vues

| Vue | Contenu |
|---|---|
| **Tiers** | Tier list S→D, paliers recalculés selon les filtres actifs |
| **Stats** | Tableau triable : stats de base, indice, ses trois composantes, confiance, sources |
| **Équipe** | Constructeur d'équipe avec note de synergie |
| **Réglages** | Poids modifiables en direct, validation hors-source des 6 tier lists |
| **Méthode** | Le modèle complet et les limites connues |

Filtres : roster, rôle, élément (9), stade, masquer les formes identiques, recherche.
Clic sur une carte → fiche détaillée : décomposition du score, lecture du kit sur les six
axes, verrou élémentaire éventuel, synergie, traits et compétences.

## Une compétence, une notation

`kits.json` note le kit entier ; `kit_skills.json` le décompose **compétence par
compétence**, de 0 à 3 sur chacun des six axes, plus une part *toujours active* (ultime,
attaque de base, traits) propre à chaque Aniimo. Le jeu n'autorisant que **deux compétences
équipées**, `score.py` retient la meilleure paire pour le rôle et ramène chaque axe à ce que
cette paire délivre réellement.

Les notes appartiennent à la **compétence**, jamais au couple (Aniimo, compétence) : deux
Aniimo qui lancent le même sort en reçoivent forcément la même note. Un nom ne porte
plusieurs notations que s'il porte plusieurs textes de jeu — un seul cas, `Ballistic Guard`
(lignée Helmut contre lignée Rookey). Ce choix a corrigé **38 divergences** de saisie :
38 compétences notées différemment selon leur porteur alors qu'elles ne portent qu'un seul
texte dans le jeu. La part *toujours active* n'est alignée entre une base et sa forme que
lorsque le jeu ne les distingue en rien — ni innés, ni liste de compétences.

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

L'**indice de confiance** est mesuré par `score.py` sur **400 tirages** où tout ce qui est
incertain bouge à la fois : chaque poids perturbé de ±25 %, chaque note de kit relue par un
autre lecteur (±1 deux fois sur trois), et les sept avis (6 tier lists + le calcul)
rééchantillonnés avec remise — autrement dit : *qu'aurait donné ce classement avec d'autres
sources ?* C'est un test bien plus dur qu'une simple perturbation des poids, et les taux ne
se comparent pas à ceux d'une version antérieure.

Chaque entrée reçoit un badge : **sûr** (49) garde son palier dans au moins 75 % des tirages
*et* est classée par au moins deux sources ; **incertain** (35) n'est classée par aucune
source, ou ses tirages s'étalent sur trois paliers ; **probable** (131) est le reste, en
général à cheval sur deux paliers. Taux de maintien moyen : **66,2 %**, 126 entrées sur 215
au-dessus de 60 %.

Le seuil des 75 % porte sur le **taux arrondi**, celui que la page affiche à côté du badge :
un Aniimo annoncé à 75 % ne doit pas être dit « probable » parce que le calcul exact valait
74,8. Les huit entrées que la seconde source a fait entrer au roster portent toutes
« incertain », et pour une raison qui n'a rien d'un défaut : **aucune tier list publiée ne
les classe encore**. Wavwal sort 3ᵉ au général avec ce badge — son total de base, 575, est le
plus haut du roster, mais rien d'extérieur ne le confirme.

## Recoupement avec le consensus

Le classement n'est pas calé sur les tier lists publiées, mais il est recoupé avec **six**
d'entre elles (Game8, AniimoGuide, AllThings, KongBakPao, Mobi, PowerUp). Chacune est ramenée
en percentile de rang à l'intérieur d'elle-même — peu importe qu'elle ait quatre paliers ou
sept. Son poids est son **accord de rang avec la moyenne des autres, au carré** : une source
qui classe au hasard pèse ~0, et deux sources qui se recopient ne comptent pas double. Le
calcul pèse comme une source de plus (0,53).

La vue **Réglages** affiche la validation **hors-source** : chaque tier list est mise de côté
à tour de rôle puis prédite sans elle. Lecture : quand « indice final » rejoint « les autres
experts », le modèle devine un avis qu'il n'a pas vu aussi bien que les experts se devinent
entre eux — et ceux-ci ne s'accordent qu'entre 0,45 et 0,78.

Sur les **84** Aniimo que Game8 classe : **36 %** de paliers identiques, **90 %** à un palier
près, corrélation des rangs **0,71**, et **8** écarts de deux paliers ou plus. Ces quatre
chiffres ne sont pas recopiés à la main : `smoke.js` les recalcule à chaque exécution, les
imprime, et échoue si l'accord se dégrade (section *9b*).

Les écarts ne sont pas des erreurs à corriger. Le motif dominant est net : les tier lists
communautaires notent plus haut les DPS à burst conditionnel et plus bas les Break et
Support à grosses stats. C'est cohérent — elles jugent la facilité de jeu réelle, ce modèle
juge le plafond à investissement maximal.

## Deux sources, aucune d'elles arbitre

Game8 a été la source unique jusqu'ici. Elle a deux trous : elle n'a pas encore rédigé les
Aniimo à partir du **N° 084**, et elle ne publie ni la Puissance, ni le coût en EP, ni le
temps de recharge d'une compétence — les trois chiffres qui permettraient de *calculer* un
kit au lieu de le noter à la main. `aniidex.com` publie les deux.

`audit.py` confronte les deux relevés et **ne tranche jamais** : quand ils divergent, les
deux valeurs restent côte à côte dans `raw/_audit.json`, à vérifier dans le jeu. État au
21/09/2026, sur les 88 bases communes :

| | |
|---|---|
| Éléments | **0** divergence — accord parfait |
| Stats | **5** : Fennelun, Helion, Leafy, Lunara, Nimbi |
| Rôle | **5** : Blazen, Bolty, Fulmintis, Infergon, Somniwing |
| Compétences | **44**, dont 41 où aniidex est un *sous-ensemble* de Game8 |

Les 41 sous-ensembles ne sont pas un désaccord mais une précision de plus : Game8 empile sur
la fiche de base les compétences de **toutes** ses formes régionales, aniidex les sépare
forme par forme. Restent **11 vrais désaccords**, listés dans `raw/_audit.json`.

`audit.py` y ajoute deux tests qui ne demandent rien d'autre que les données publiées, et
qui ne tranchent toujours pas — ils disent seulement laquelle des deux sources est cohérente
avec elle-même :

- **Une ligne de statistiques prêtée à plusieurs Aniimo n'est pas une donnée.** aniidex donne
  la même ligne 100/116/72/90/72/64 à Lunara, Fennelun, Helion **et** Soleon, et Game8 la
  dément pour les trois qu'il publie. Une ligne recopiée d'une fiche sur ses voisines ne
  prouve rien sur aucune d'elles.
- **Un rôle doit s'accorder avec la statistique dont ce rôle vit.** Un Break dont le BREAK
  passe sous l'Attaque se contredit lui-même. Sur les 5 désaccords de rôle, Game8 est
  cohérent et aniidex ne l'est pas pour Blazen (ATQ 100 / BREAK 104), Bolty (85/87),
  Fulmintis (130/50) et Infergon (125/50). Le test ne sait rien dire des rôles de soutien, et
  il le dit : Somniwing (Regen contre Support) reste indécidable.

Restent donc **7 désaccords** qui demandent une vérification dans le jeu : Bonesky,
Fennelun, Helion, Leafy, Lunara, Nimbi, Somniwing.

Ce qu'aniidex apporte et qui n'est pas encore exploité : **262 compétences chiffrées**
(Puissance / EP / recharge / étiquettes Dégâts, Contrôle, Statut anormal, Soin…) et
**50 versions améliorées** de compétences — la matière du futur simulateur d'éveil.

## Ce qui manque au roster

Sur les douze Aniimo que Game8 n'a pas encore rédigés, **six sont entrés** au roster parce
que la seconde source en publie les quatre éléments nécessaires : **Reefish** (084),
**Coraliz** (085), **Cheekie** (086), **Wavwal** (087), **Malangel** (092) et **Malevsera**
(093), plus les formes **Rainstorm Reefish** et **Rainstorm Coraliz**. Leurs kits ont été lus
à la main contre `RUBRIC.md` comme les 116 autres — c'est le lot `kits/b7.json`.

**Six restent en attente**, nommés dans `raw/_attente.json` et affichés tels quels dans la
vue Méthode :

| Aniimo | Ce qui manque |
|---|---|
| Bubbeep, Glameep, Popapus, Gachapus, Sparkelf | pas de rôle publié |
| Soleon | statistiques non attestées (ligne partagée avec Fennelun, Helion, Lunara) |

On ne leur invente ni rôle ni statistique. Ils étaient déjà cités par les tier lists externes
sans que `ext_tiers.py` le dise ; il conserve maintenant ces noms (champ `hors_roster`) et
signale ceux que **deux sources au moins** citent. Trois noms restent cités sans être
trouvables dans aucune des deux sources : `Witchin`, `Witchin (Prismana Form)` et
`Thornblade (Rainstorm Form)`.

## Limites connues

- **P.Déf est une valeur dérivée.** Le tableau source duplique l'Attaque dans la cellule
  P.Déf — vérifié sur les 207 fiches Game8, sans une seule exception. Le Total de base étant
  correct, P.Déf est reconstruit par soustraction.
- **Lunara** affiche chez Game8 ATQ 64 / P.Déf 116 pour un DPS. Les deux ordres donnent le
  même Total de 514, et Game8 seule ne permet pas de trancher. La correction envisagée sur la
  foi de la seconde source a été **abandonnée** : aniidex prête la même ligne à Lunara,
  Fennelun, Helion et Soleon, et Game8 la dément pour les trois qu'il publie. Cette source ne
  sait donc rien de particulier sur Lunara, elle applique une ligne de famille. La valeur de
  Game8 est conservée et la question reste ouverte jusqu'à une lecture en jeu.
- **Soleon** est écarté pour la même raison : sa seule ligne de statistiques est celle,
  partagée, de la famille Lumière. Game8 ne le publie pas (N° 9999, `??` partout).
- **Éléments des formes régionales.** Ils sont lus sur les tuiles de la fiche aniidex, dont
  les icônes portent le nom interne du jeu : `Rock` pour Terre, `Electric` pour Foudre,
  `Holy` pour Lumière. La lecture est validée sur les **119 formes** que les deux sources
  décrivent l'une et l'autre : **119/119** d'accord exact avec Game8. C'est ce qui autorise à
  en dériver Rainstorm Reefish et Rainstorm Coraliz, que Game8 ne publie pas.
- Le modèle ne mesure ni la vitesse d'animation, ni la portée, ni le confort de jeu.
- Les paliers sont des percentiles : une position relative dans le vivier affiché, pas une
  puissance absolue. Changer un filtre les recalcule.

## L'interface

Aucune dépendance, aucun CDN : `index.html` porte tout son style et tout son script, et les
deux polices — Baloo 2 pour les titres, Nunito pour le texte — sont servies depuis `fonts/`
par des règles `@font-face` écrites en tête de la feuille de style. 14 fichiers `.woff2`,
469 Ko, sous-ensembles latin et latin-ext seulement : c'est tout ce qu'un texte français
réclame, et le site s'affiche tel quel hors ligne.

- **Jour et nuit.** Le thème par défaut est le parchemin ; la lune du bandeau passe à la
  veillée. Tout est en variables CSS sur `:root`, redéfinies sous `html[data-theme=nuit]` —
  aucune couleur n'est écrite deux fois. Le choix tient dans `localStorage` (`amoTheme`) ;
  sans choix enregistré, on suit le réglage du système.
- **Écrans étroits.** Sous 760 px le bandeau se comprime et ses onglets défilent, les filtres
  passent en pleine largeur, les cartes rétrécissent, et les tableaux larges défilent *dans
  leur carte* au lieu de pousser la page. Sous 420 px les cartes rétrécissent encore. Aucune
  vue ne déborde horizontalement.
- **Le texte est en français accentué**, y compris ce que `score.py` écrit dans `data.js` :
  les notes de kit, les libellés d'axes, les noms d'éléments et les personnalités. Les noms
  de compétences et leurs descriptions restent dans la langue du jeu.

## Banc d'essai

Harnais jsdom (le site n'a pas de dépendance, le test si) :

```bash
cd /d/REPOS/amo && npm install   # une fois, installe jsdom dans le dossier
npm test                         # = node smoke.js
```

89 assertions : conformité du recalcul client au `score.py` de référence, tier list unique,
alignement des entrées identiques sur leur base, puces de roster cumulables, badges `=` et
badges de confiance, filtres, modale, tri du tableau, constructeur d'équipe de bout en bout,
curseurs de poids, validation hors-source, accord avec Game8 recalculé, contenu de la page
Méthode confronté au modèle qui tourne (poids des six sources, tirages de confiance, kits
verrouillés et duos nommés), cohérence de l'indice de confiance, et la
correspondance entre `raw/_attente.json` et le tableau des Aniimo annoncés mais pas classés,
et le modèle de potentiel : croissance au plafond, facteur de couronne, héritage exact de la
recommandation du jeu par les formes, et présence de tout cela sur la fiche. Une
dernière section garde l'autonomie du site : aucune ressource ne doit venir d'un domaine
distant, et chaque `@font-face` doit pointer un `.woff2` qui existe bel et bien dans
`fonts/`.

`node_modules/` est ignoré par git : le site, lui, n'a toujours aucune dépendance.
