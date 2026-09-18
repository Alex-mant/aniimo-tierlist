# Grille de lecture des kits

Chaque kit reçoit 6 notes de 0 à 10, une conditionnalité de 0 à 3, et une phrase.
Les notes sont **absolues** (pas relatives au roster) pour rester stables si le
roster change.

| Axe | 0 | 5 | 10 |
|---|---|---|---|
| `dmg` | aucun apport de dégâts propre | un multiplicateur net ou un cumul correct | plusieurs multiplicateurs, crit et cumuls qui se composent |
| `team` | rien pour les alliés | un buff d'équipe simple | buff large, fort, et non verrouillé sur un élément |
| `brk` | aucun outil de BREAK | contribution correcte | génère ou amplifie le BREAK de toute l'équipe |
| `sust` | aucune survie | soin ou bouclier ponctuel | soin de zone fort, réduction de dégâts, purge |
| `res` | aucune ressource | rend un peu d'EP | batterie d'EP pour l'équipe |
| `ctrl` | aucun contrôle ni debuff | un contrôle ou une réduction de résistance | contrôle fiable + shred significatif |

`cond` : 0 = s'applique toujours · 1 = une condition simple · 2 = cumuls ou
positionnement à entretenir · 3 = plusieurs conditions empilées.

Un buff verrouillé sur un élément est plafonné à 6 en `team` : il ne vaut que
dans une composition dédiée.

**Exception au plafond** : un buff verrouille sur un element mais d'une ampleur
exceptionnelle (>= 50 %) peut monter a 7. Un +70 % de degats critiques ne se compare
pas a un +8 % generique, meme en composition dediee.
