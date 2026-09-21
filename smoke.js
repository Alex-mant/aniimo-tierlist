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

console.log("\n== 10. annonces, pas encore classes ==");
click('[data-v="meth"]');
ok(Array.isArray(M.attente), M.attente.length + " Aniimo annonces sans fiche complete");
ok($$("table.wait tbody tr").length === M.attente.length,
   "la vue Methode les nomme tous (" + $$("table.wait tbody tr").length + " lignes)");
ok(M.attente.every(a => !A.some(r => r.name === a.name)),
   "aucun d'eux n'est classe dans la tier list");
ok(M.attente.every(a => a.manque && a.manque.length),
   "chacun dit ce qui lui manque");

console.log("\n== erreurs JS =="); console.log(errs.length ? errs : "  aucune");
console.log(ko ? "\nRESULTAT : " + ko + " test(s) en echec" : "\nRESULTAT : tout passe");
process.exit(ko || errs.length ? 1 : 0);
