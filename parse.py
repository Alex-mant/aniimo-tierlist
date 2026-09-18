# -*- coding: utf-8 -*-
"""Parse les fiches Game8 scrapees dans raw/ -> raw/parsed.json"""
import io, re, json, glob, os

ELEMENTS = ["Fire", "Water", "Grass", "Wind", "Earth", "Ice", "Lightning", "Dark", "Light"]
ROLES = ["DPS", "Break", "Support", "Regen", "Heal"]
STAGES = ["Lumin", "Gamma", "Nova"]


def to_text(path):
    h = io.open(path, encoding="utf-8", errors="replace").read()
    h = re.sub(r"<(script|style|template)[^>]*>.*?</\1>", "", h, flags=re.S)
    h = re.sub(r"<img[^>]*>", "", h)
    h = re.sub(r"</t[dh]>", "|", h)
    h = re.sub(r"</tr>", "\n", h)
    h = re.sub(r"<h([23])[^>]*>", r"\n## ", h)
    h = re.sub(r"</h[23]>", "\n", h)
    t = re.sub(r"<[^>]+>", "", h)
    t = t.replace("&#39;", "'").replace("&amp;", "&").replace("&quot;", '"').replace("&nbsp;", " ")
    t = re.sub(r"[ \t]*\n[ \t\n]*", "\n", t)
    return re.sub(r"\n{2,}", "\n", t)


def section(t, header, stop="\n## "):
    i = t.find("\n## " + header + "\n")
    if i < 0:
        return ""
    i += len(header) + 5
    j = t.find(stop, i)
    return t[i:j if j > 0 else len(t)]


def pairs(block):
    """Un bloc 'Nom\n|\nDescription|' -> [(nom, desc)]"""
    lines = [l.strip() for l in block.split("\n") if l.strip() and l.strip() != "|"]
    out = []
    i = 0
    while i + 1 < len(lines):
        nm = lines[i].rstrip("|").strip()
        ds = lines[i + 1].rstrip("|").strip()
        if nm and ds and len(nm) < 45 and len(ds) > 15:
            out.append((nm, ds))
            i += 2
        else:
            i += 1
    return out


def parse(path):
    t = to_text(path)
    name = os.path.basename(path)[:-5].replace("_", " ")

    i = t.find("Base Stats\nNo. ")
    if i < 0:
        return None
    blk = t[i:i + 1400]

    no = re.search(r"No\. ?([0-9A-Za-z]+)\|", blk)
    stats = {}
    for key, lbl in [("hp", "HP"), ("pdef", "P.Def"), ("atk", "Attack"),
                     ("mdef", "M.Def"), ("brk", "Break"), ("reg", "Regen")]:
        m = re.search(r"\n%s\|\n(\d+)\|" % re.escape(lbl), blk)
        if not m:
            return None
        stats[key] = int(m.group(1))
    tot = re.search(r"\nBase Total\|\n(\d+)\|", blk)
    # Bug de template Game8 : la cellule P.Def recopie la valeur d'Attack.
    # Le Base Total affiche, lui, est correct -> on reconstruit P.Def par difference.
    if tot:
        stats["pdef"] = int(tot.group(1)) - (stats["hp"] + stats["atk"] + stats["mdef"]
                                             + stats["brk"] + stats["reg"])

    head = blk[:blk.find("Homeland Abilities")] if "Homeland Abilities" in blk else blk
    els = [e for e in ELEMENTS if re.search(r"\n%s\n" % e, head)]
    role = next((r for r in ROLES if re.search(r"\n%s\n" % r, head)), None)
    stage = next((s for s in STAGES if s + " Stage" in head), None)

    hl = re.search(r"Homeland Abilities\|\n(.*?)\n\|\nAbilities", blk, re.S)
    homeland = re.findall(r"([A-Za-z ]+)\n- Lv\. (\d+)", hl.group(1)) if hl else []
    pf = re.search(r"Pathfinding\|\n(.*?)\|", blk, re.S)
    mob = re.search(r"Mobility\|\n([^|\n]+)", blk)
    log = re.search(r"Aniilog Entry\|\n(.*?)\|", blk, re.S)

    traits = pairs(section(t, name + " Traits"))
    skills = pairs(section(t, "All " + name + " Combat Skills"))
    innate = pairs(section(t, "All " + name + " Innate Skills"))

    forms = re.findall(r"([A-Z][A-Za-z' ]+)\(No\. ?([0-9A-Za-z]+)\)",
                       section(t, name + "'s Other Forms"))

    kind = "prismana" if name.startswith("Prismana ") else (
        "alpha" if name.startswith("Alpha ") else (
            "form" if (no and re.search(r"[B-Z]$", no.group(1)) and " " in name) else "base"))

    return {
        "name": name, "no": no.group(1) if no else None, "kind": kind,
        "el": els, "role": role, "stage": stage,
        "stats": stats, "total": int(tot.group(1)) if tot else sum(stats.values()),
        "homeland": [[a.strip(), int(b)] for a, b in homeland],
        "pathfinding": pf.group(1).strip().replace("\n", " ") if pf else None,
        "mobility": mob.group(1).strip() if mob else None,
        "traits": [{"n": a, "d": b} for a, b in traits],
        "skills": [{"n": a, "d": b} for a, b in skills],
        "innate": [{"n": a, "d": b} for a, b in innate],
        "log": log.group(1).strip().replace("\n", " ") if log else None,
        "forms": [[a.strip(), b] for a, b in forms],
    }


out, bad = [], []
for p in sorted(glob.glob("raw/*.html")):
    if os.path.basename(p).startswith("_"):
        continue
    try:
        r = parse(p)
    except Exception as e:
        r, err = None, e
    if r:
        out.append(r)
    else:
        bad.append(os.path.basename(p))

io.open("raw/parsed.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))

import collections
c = collections.Counter(r["kind"] for r in out)
print("parsed=%d  %s" % (len(out), dict(c)))
print("sans stats (%d): %s" % (len(bad), ", ".join(bad[:12])))
miss = [r["name"] for r in out if not r["role"] or not r["el"]]
print("role/element manquant (%d): %s" % (len(miss), ", ".join(miss[:12])))
print("sans trait: %d | sans skill: %d" % (sum(1 for r in out if not r["traits"]),
                                           sum(1 for r in out if not r["skills"])))
