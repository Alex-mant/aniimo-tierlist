// Banc d'essai du site : on charge index.html dans un DOM, on clique, et on
// verifie que ce que la page affiche redit bien ce que score.py a calcule.
//
//     npm install          (une fois, installe jsdom dans ce dossier)
//     node smoke.js
const {JSDOM, VirtualConsole} = require('jsdom'), fs = require('fs'),
      P = require('path').join(__dirname, '/');
const html = fs.readFileSync(P + 'index.html', 'utf8').replace(
  '<script src="data.js"></script>',
  '<script>' + fs.readFileSync(P + 'data.js', 'utf8') + '\nwindow.__A=ANIIMO;window.__M=META;</script>');
const errs = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => errs.push("jsdom: " + e.message));
const dom = new JSDOM(html, {
  runScripts: "dangerously", url: "http://127.0.0.1:8777/", virtualConsole: vc,
  beforeParse(w) { w.addEventListener("error", e => errs.push("window error: " + e.message)); }
});
const w = dom.window, d = w.document;
const $ = s => d.querySelector(s), $$ = s => [...d.querySelectorAll(s)];
const click = s => { const e = $(s); if (!e) throw new Error("introuvable: " + s); e.click(); };
const clickTxt = (sel, txt) => {
  const e = $$(sel).find(x => x.textContent.trim() === txt);
  if (!e) throw new Error("bouton introuvable: " + txt); e.click();
};
const fire = (el, type) => el.dispatchEvent(new w.Event(type, { bubbles: true }));
// chaque rendu remplace la barre de filtres : toujours re-interroger le DOM vivant
const set = (sel, val, type) => { const e = $(sel); if (!e) throw new Error("introuvable: " + sel);
  if (type === "check") e.checked = val; else e.value = val;
  fire(e, type === "check" ? "change" : type); };
let ko = 0;
const ok = (c, m) => { if (!c) ko++; console.log((c ? "  ok   " : "  KO   ") + m); };

const A = w.__A, M = w.__M, TIERS_C = ["S","A","B","C","D"];
const nSameOf = k => A.filter(r => r.kind === k && r.same).length;

console.log("\n== 1. recalcul client contre score.py (poids par defaut) ==");
// data.js arrondit au dixieme et statParts aussi : l'ecart admissible cumule
// deux arrondis de 0,05, soit 0,11 au pire.
for (const pair of [["_st", "sStat"], ["_ki", "sKit"], ["_sy", "sSyn"], ["_sc", "score"]]) {
  let worst = 0, wn = "";
  for (const r of A) {
    const dd = Math.abs(r[pair[0]] - r[pair[1]]);
    if (dd > worst) { worst = dd; wn = r.name; }
  }
  ok(worst < 0.11, pair[1] + " : ecart max " + worst.toFixed(4) + " (" + wn + ")");
}

console.log("== 2. une seule tier list ==");
ok($$(".kindblk").length === 1, "un seul bloc de classement");
ok($$(".row").length === 5, "5 lignes de paliers");
ok($$(".card").length === A.length, $$(".card").length + " cartes = les " + A.length + " entrees");
const t0 = $$(".row").map(r => r.querySelectorAll(".card").length);
ok(t0.every(x => x > 0), "aucun palier vide : " + t0.join("/"));
ok($$(".card img").every(i => i.getAttribute("src").endsWith(".png")), "toutes les cartes ont une image");
const nConf = $$(".bd.ok, .bd.warn, .bd.uns").length;
ok(nConf > 0, nConf + " badges de confiance (sur / probable / incertain)");
ok(A.filter(r => r.ref).length > 0,
   A.filter(r => r.ref).length + " entrees comparables a Game8 (champ ref conserve)");

const TI = t => TIERS_C.indexOf(t);
const byN = {}; A.forEach(r => byN[r.name] = r);
const split = A.filter(r => r.same && byN[r.parent]
  && (Math.abs(r.fin - byN[r.parent].fin) > 1e-9 || r._tier !== byN[r.parent]._tier));
ok(split.length === 0, "les " + A.filter(r => r.same).length
   + " entrees identiques a leur base finissent au meme rang qu'elle"
   + (split.length ? " -- ecart : " + split.map(r => r.name).join(", ") : ""));
const diff = A.filter(r => r.kind === "prismana" && byN[r.parent] && !r.same
  && r._sc >= byN[r.parent]._sc - 1e-9 && TI(r._tier) > TI(byN[r.parent]._tier));
ok(diff.every(r => r.skills.length !== byN[r.parent].skills.length
                || r.el.length !== byN[r.parent].el.length),
   diff.length + " Prismana classee(s) sous leur base : toutes different du jeu"
   + (diff.length ? " (" + diff.map(r => r.name).join(", ") + ")" : ""));
ok(nSameOf("prismana") === 5, nSameOf("prismana") + " Prismana identiques a leur base");
ok($$(".card .bd.same").length === M.nSame,
   $$(".card .bd.same").length + ' badges "=" sur les cartes = ' + M.nSame);
console.log("         Prismana par palier : " +
  TIERS_C.map(t => t + " " + A.filter(r => r.kind === "prismana" && r._tier === t).length).join(" · "));

console.log("");
console.log("== 2b. les rosters sont des filtres cumulables ==");
click('[data-k="prismana"]');                      // on retire les Prismana
ok($$(".card").length === A.length - M.n.prismana,
   "sans Prismana : " + $$(".card").length + " = " + (A.length - M.n.prismana));
ok(!$$(".card").some(c => /^Prismana /.test(c.dataset.n)), "plus aucune Prismana affichee");
ok($$(".kindblk").length === 1, "toujours un seul classement");
click('[data-k="form"]');                          // puis les formes regionales
ok($$(".card").length === M.n.base, "Normaux seuls : " + $$(".card").length + " = " + M.n.base);
click('[data-k="base"]');
ok($$(".card").length === M.n.base, "on ne peut pas vider le vivier : " + $$(".card").length);
click('[data-k="prismana"]');                      // on les remet
ok($$(".card").length === M.n.base + M.n.prismana, "Normaux + Prismana : " + $$(".card").length);
click('[data-k="all"]');
ok($$(".card").length === A.length, "bouton Tous : retour aux " + A.length);

console.log("");
console.log("== 2c. formes identiques ==");
ok($$(".card .bd.same").length === M.nSame, M.nSame + ' badges "=" sur les cartes');
set("#fh", true, "check");
ok($$(".card").length === A.length - M.nSame,
   "masquer les identiques : " + $$(".card").length + " = " + (A.length - M.nSame));
ok($$(".card .bd.same").length === 0, "plus aucune carte marquee =");
set("#fh", false, "check");

console.log("\n== 3. filtres ==");
set("#fr", "Heal", "change");
ok($$(".card").length === A.filter(r => r.role === "Heal").length,
   "role Heal : " + $$(".card").length + " = " + A.filter(r => r.role === "Heal").length);
set("#fe", "Ice", "change");
ok($$(".card").length === A.filter(r => r.role === "Heal" && r.el.includes("Ice")).length, "Heal + Glace cumules");
set("#fr", "", "change"); set("#fe", "", "change");
set("#fq", "prismana", "input");
ok($$(".card").length === A.filter(r => /prismana/i.test(r.name)).length, "recherche 'prismana'");
set("#fq", "", "input");

console.log("\n== 4. modale ==");
$(".card").click();
ok($("#ov").className.includes("on"), "la modale s'ouvre");
ok($("#modal").textContent.includes("Lecture du kit"), "elle contient la lecture du kit");
ok($$("#modal .axr").length >= 12, $$("#modal .axr").length + " barres (6 stats + 6 axes)");
click("#cl");
ok(!$("#ov").className.includes("on"), "elle se ferme");

console.log("\n== 5. vue Stats ==");
clickTxt("#nav button", "Stats");
ok($$("tbody tr").length === A.length, $$("tbody tr").length + " lignes = " + A.length);
const col = i => $$("tbody tr").map(r => +r.children[i].textContent);
$$("th[data-s]").find(t => t.dataset.s === "atk").click();
const atk = col(4);
ok(atk.every((v, i) => i === 0 || atk[i - 1] >= v), "tri decroissant par ATQ");
$$("th[data-s]").find(t => t.dataset.s === "atk").click();
const atk2 = col(4);
ok(atk2.every((v, i) => i === 0 || atk2[i - 1] <= v), "second clic : tri croissant");

console.log("\n== 6. constructeur d'equipe ==");
clickTxt("#nav button", "Équipe");
ok($$(".slot").length === 4, "4 emplacements");
click("#autoteam");
// le bouton ne compose plus une equipe, il en propose plusieurs : une qui
// touche a tout, puis une par element. On adopte la premiere pour la suite.
const props = $$(".prop");
ok(props.length >= 4, props.length + " compositions proposees");
ok(props.every(p => p.querySelectorAll(".card").length === 4),
   "chaque proposition compte 4 membres");
ok(props.every(p => p.querySelector("[data-prop]")), "chacune a son bouton d'adoption");
{ const noms = props.map(p => p.querySelector(".pn").textContent.trim());
  ok(new Set(noms).size === noms.length, "des noms distincts : " + noms.join(", "));
  const notes = props.map(p => parseFloat(p.querySelector(".sub").textContent.match(/note\s+([\d.]+)/)[1]));
  ok(notes.slice(1).every((n, i) => n <= notes[i] + 1e-9), "classees de la meilleure note a la moindre");
  const sigs = props.map(p => [...p.querySelectorAll(".card .nm")].map(e => e.textContent.trim()).sort().join("|"));
  ok(new Set(sigs).size === sigs.length, "aucune proposition n'est le doublon d'une autre"); }
$("[data-prop]").click();
ok($$(".prop").length === 0, "les propositions disparaissent une fois l'equipe adoptee");
ok($$(".slot.full").length === 4, "composition automatique : 4 membres");
const note = parseFloat($(".big").textContent);
ok(note > 0 && note <= 100, "note d'equipe = " + note + "/100");
ok(["S", "A", "B", "C", "D"].includes($(".grade").textContent.trim()), "lettre = " + $(".grade").textContent.trim());
ok($$(".li.up").length > 0, $$(".li.up").length + " points forts listes");
console.log("         equipe proposee :", $$(".slot.full .n").map(e => e.textContent.trim()).join(" | "));
console.log("         manques listes  :", $$(".li.dn").length);
$$(".li.up").slice(0, 4).forEach(e => console.log("         + " + e.textContent.trim().slice(0, 110)));
$$(".li.dn").slice(0, 3).forEach(e => console.log("         - " + e.textContent.trim().slice(0, 110)));
click('[data-rm="0"]');
ok($$(".slot.full").length === 3, "retrait d'un membre");
click('[data-add="0"]');
ok($$(".panel h2").some(h => h.textContent.includes("Choisir")), "le selecteur s'ouvre");
$(".panel .cards .card").click();
ok($$(".slot.full").length === 4, "selection d'un remplacant");
click("#clearteam");
ok($$(".slot.full").length === 0, "vider l'equipe");

console.log("\n== 6b. les noyaux elementaires en sont vraiment ==");
// Une equipe « Noyau Feu » qui n'aligne pas trois porteurs de Feu ne tient pas
// sa promesse : c'est tout l'interet de la proposer a cote de la meilleure note.
click("#clearteam");
click("#autoteam");
{ const EL = {Feu:"Fire", Eau:"Water", Herbe:"Grass", Vent:"Wind", Terre:"Earth", Glace:"Ice",
              Foudre:"Lightning", "Ténèbres":"Dark", "Lumière":"Light"};
  const noyaux = $$(".prop").filter(p => /^Noyau /.test(p.querySelector(".pn").textContent.trim()));
  ok(noyaux.length >= 3, noyaux.length + " noyaux elementaires proposes");
  const faux = noyaux.filter(p => {
    const e = EL[p.querySelector(".pn").textContent.trim().replace("Noyau ", "")];
    const n = [...p.querySelectorAll(".card .nm")]
      .filter(x => (byN[x.textContent.trim()] || {el: []}).el.includes(e)).length;
    return !(e && n >= 3);
  });
  ok(faux.length === 0, "chaque noyau aligne au moins 3 porteurs de son element"
     + (faux.length ? " (" + faux[0].querySelector(".pn").textContent.trim() + ")" : ""));
  noyaux.slice(0, 3).forEach(p => console.log("         " + p.querySelector(".pn").textContent.trim()
    + " : " + [...p.querySelectorAll(".card .nm")].map(e => e.textContent.trim()).join(" | ")));
  // un membre garde doit se retrouver dans toutes les propositions
  $("[data-prop]").click();
  click('[data-lock="0"]');
  const garde = $$(".slot.full .n")[0].textContent.trim();
  click("#autoteam");
  ok($$(".prop").every(p => [...p.querySelectorAll(".card .nm")].some(e => e.textContent.trim() === garde)),
     "le membre garde (" + garde + ") est dans chaque proposition"); }
click("#clearteam");

console.log("\n== 7. reglages : poids et calibration ==");
clickTxt("#nav button", "Réglages");
const cal0 = $("#validbody").textContent;
ok(/0\.\d\d/.test(cal0), "validation hors-source rendue : "
   + (cal0.match(/0\.\d\d/g) || []).slice(0, 3).join(" / "));
const sl = $$('input[data-w]').find(i => i.dataset.w === "Mélange|kit");
ok(!!sl, "curseur Melange|kit present");
const sc0 = A[0]._sc;
sl.value = "0.9"; fire(sl, "input");
ok(A[0]._sc !== sc0, "deplacer un curseur change les scores");
ok($("#validbody").textContent !== cal0, "la validation se recalcule");
click("#resetw");
ok(Math.abs(A[0]._sc - sc0) < 1e-9, "reinitialisation des poids");

console.log("\n== 8. indice de confiance (mesure par score.py) ==");
const keeps = A.map(r => r.keep);
ok(keeps.length === A.length, keeps.length + " entrees portent un taux de maintien");
ok(keeps.every(v => v >= 0 && v <= 100), "pourcentages dans [0,100]");
ok(A.every(r => ["sur", "probable", "incertain"].indexOf(r.conf) >= 0),
   "chaque entree porte un niveau de confiance");
const CO = { sur: 3, probable: 2, incertain: 1 };
const lvl = r => (Object.keys(r.ext).length === 0 || r.span.length >= 3) ? "incertain"
                 : (r.keep >= 75 && Object.keys(r.ext).length >= 2) ? "sur" : "probable";
const wrong = A.filter(r => lvl(r) !== r.conf);
ok(wrong.length === 0, "le niveau de confiance suit sources + largeur d'intervalle"
   + (wrong.length ? " -- " + wrong.slice(0, 3).map(r => r.name).join(", ") : ""));
console.log("         mesure sur", M.runs, "tirages | instables (<60%) :",
            keeps.filter(v => v < 60).length,
            "| moyenne :", (keeps.reduce((a, b) => a + b, 0) / keeps.length).toFixed(1) + "%");
ok(Math.abs(A[0]._sc - sc0) < 1e-9, "poids de reference restaures");

console.log("\n== 9. methode ==");
clickTxt("#nav button", "Méthode");
ok($(".meth").textContent.includes(String(M.nKits)), "mentionne les " + M.nKits + " kits lus");
ok($(".meth").textContent.includes(String(A.length)), "mentionne les " + A.length + " entrees");
ok(!$("#filters").innerHTML.trim(), "les filtres sont masques sur Methode");
// la page Methode doit decrire le modele qui tourne, pas un modele d'avant :
// les sources, l'indice de confiance et les loadouts s'y comptent en direct.
const nSrc = Object.keys(M.src).length;
ok($$("table.wait.src tbody tr").length === nSrc,
   "les " + nSrc + " tier lists sont listees avec leur poids");
ok(Object.keys(M.src).every(k => $(".meth").textContent.includes(M.src[k].w.toFixed(2))),
   "chaque poids de source est affiche");
ok($(".meth").textContent.includes(String(M.runs)),
   "annonce les " + M.runs + " tirages de l'indice de confiance");
for (const c of ["sur", "probable", "incertain"])
  ok($(".meth").textContent.includes(String(A.filter(r => r.conf === c).length)),
     "compte les entrees " + c);
ok($(".meth").textContent.includes(String(Object.keys(M.lock).length))
   && $(".meth").textContent.includes(String(M.duos.length)),
   "dit combien de kits sont verrouilles et combien de duos sont nommes");

console.log("\n== 9b. ecart avec Game8 (le chiffre publie dans le README) ==");
// Le README annonce l'accord avec Game8 ; ce bloc le recalcule pour qu'il ne
// puisse pas vieillir en silence, et refuse qu'il s'effondre.
{
  const p = A.filter(r => r.ref);
  const ti = x => TIERS_C.indexOf(x);
  const memes = p.filter(r => r.ref === r._tier).length;
  const proches = p.filter(r => Math.abs(ti(r.ref) - ti(r._tier)) <= 1).length;
  const loin = p.filter(r => Math.abs(ti(r.ref) - ti(r._tier)) >= 2).length;
  const rang = v => { const o = [...v.keys()].sort((a, b) => v[a] - v[b]), r = [];
    for (let i = 0; i < v.length; ) { let j = i;
      while (j + 1 < v.length && v[o[j + 1]] === v[o[i]]) j++;
      for (let k = i; k <= j; k++) r[o[k]] = (i + j) / 2 + 1; i = j + 1; } return r; };
  const rx = rang(p.map(r => ti(r.ref))), ry = rang(p.map(r => ti(r._tier)));
  const moy = a => a.reduce((x, y) => x + y, 0) / a.length;
  const mx = moy(rx), my = moy(ry);
  let num = 0, dx = 0, dy = 0;
  for (let i = 0; i < rx.length; i++) {
    num += (rx[i] - mx) * (ry[i] - my); dx += (rx[i] - mx) ** 2; dy += (ry[i] - my) ** 2; }
  const rho = num / Math.sqrt(dx * dy);
  console.log("         " + p.length + " compares : " + Math.round(100 * memes / p.length)
    + " % identiques, " + Math.round(100 * proches / p.length) + " % a un palier pres, "
    + loin + " ecarts de deux paliers, rho " + rho.toFixed(2));
  ok(proches / p.length >= .85, "au moins 85 % des paliers Game8 sont retrouves a un pres");
  ok(rho >= .65, "correlation des rangs avec Game8 au-dessus de 0,65");
}

console.log("\n== 10. annonces, pas encore classes ==");
click('[data-v="meth"]');
ok(Array.isArray(M.attente), M.attente.length + " Aniimo annonces sans fiche complete");
ok($$("table.wait:not(.src) tbody tr").length === M.attente.length,
   "la vue Methode les nomme tous (" + $$("table.wait:not(.src) tbody tr").length + " lignes)");
ok(M.attente.every(a => !A.some(r => r.name === a.name)),
   "aucun d'eux n'est classe dans la tier list");
ok(M.attente.every(a => a.manque && a.manque.length),
   "chacun dit ce qui lui manque");

console.log("\n== 11. potentiel : l'exemplaire parfait ==");
const POT = M.pot;
ok(Math.abs(POT.grow - (1 + POT.pt * POT.cap)) < 1e-9
   && Math.abs(POT.growFav - (1 + POT.pt * POT.capFav)) < 1e-9,
   "croissance au plafond : x" + POT.grow + " ordinaire, x" + POT.growFav + " couronnee");
ok(Math.abs(M.crown - POT.growFav / POT.grow) < 1e-4,
   "la couronne vaut +" + ((M.crown - 1) * 100).toFixed(1) + " %, pas +20 %");
ok(A.every(r => r.fav.length === 2), "chaque entree a deux stats couronnables");
ok(A.every(r => Object.keys(r.stats).every(s => Math.abs(r.grown[s]
     - r.stats[s] * (r.fav.indexOf(s) >= 0 ? POT.growFav : POT.grow)) < .06)),
   "les stats poussees suivent le plafond de potentiel de chaque stat");
ok(A.filter(r => r.reco.length).length === POT.nReco,
   POT.nReco + " entrees portent la recommandation du jeu, " + (A.length - POT.nReco)
   + " le defaut de role");
ok(A.every(r => !r.reco.length || (r.fav + "") === (r.reco + "")),
   "quand le jeu recommande, c'est lui qui decide, pas le defaut de role");
ok(A.every(r => !r.reco.length || r.recoOf),
   "chaque recommandation dit sur quelle fiche elle a ete lue");
ok(A.filter(r => r.recoOf && r.recoOf !== r.name)
    .every(r => byN[r.recoOf] && (byN[r.recoOf].reco + "") === (r.reco + "")),
   "les formes heritent exactement de la recommandation de leur base");
ok(POT.grades.length === 4 && Math.abs(POT.grades.reduce((a, g) => a + g[1], 0) - 100) < 1,
   "les 4 grades d'expertise couvrent 100 % des captures");
ok(POT.perso.length === 4 && POT.perso.every(c => c.length === 2),
   "personnalite : 4 creneaux de 2 lettres");
ok(Object.keys(POT.persoBest).length === Object.keys(M.weights).length,
   "une personnalite a viser pour chacun des " + Object.keys(M.weights).length + " roles");
click('[data-v="tier"]');
$(".card").click();
const mod = $("#modal").textContent;
ok(mod.includes("Exemplaire parfait"), "la fiche montre les stats de l'exemplaire parfait");
ok(mod.includes("Personnalité à viser"), "la fiche dit quelle personnalite viser");
ok(/recommandées par le jeu|défaut mesuré du rôle/.test(mod),
   "la fiche dit d'ou viennent ses stats couronnables");
click("#cl");

console.log("\n== 12. autonomie : ni CDN ni ressource distante ==");
// Le README promet un site qui s'affiche hors ligne. Un <link> vers Google
// Fonts avait deja reussi a s'y glisser : ce bloc est la pour la prochaine fois.
{ const brut = fs.readFileSync(P + 'index.html', 'utf8');
  // un <a href> vers une tier list est un lien, pas une ressource : seuls
  // comptent les src= et les <link>, qui eux font partir une requete.
  const dist = (brut.match(/\ssrc\s*=\s*["']https?:\/\/[^"']+/gi) || [])
    .concat(brut.match(/<link\b[^>]*https?:\/\/[^"'>]+/gi) || []);
  ok(dist.length === 0, "aucune ressource chargee depuis un domaine distant"
     + (dist.length ? " (" + dist[0].trim().slice(0, 60) + ")" : ""));
  const faces = brut.match(/@font-face\{[^}]*\}/g) || [];
  ok(faces.length >= 8, "les " + faces.length + " @font-face sont declares dans la page");
  ok(faces.every(f => /url\(fonts\/[^)]+\.woff2\)/.test(f)),
     "chaque @font-face pointe un fichier de fonts/");
  ok(faces.every(f => /font-display:\s*swap/.test(f)),
     "chaque police s'efface le temps de charger plutot que de masquer le texte");
  const manque = faces.map(f => f.match(/url\(fonts\/([^)]+)\)/)[1])
    .filter(n => !fs.existsSync(P + 'fonts/' + n));
  ok(manque.length === 0, "les fichiers de police existent vraiment"
     + (manque.length ? " (manque " + manque[0] + ")" : "")); }

console.log("\n== erreurs JS =="); console.log(errs.length ? errs : "  aucune");
console.log(ko ? "\nRESULTAT : " + ko + " test(s) en echec" : "\nRESULTAT : tout passe");
process.exit(ko || errs.length ? 1 : 0);
