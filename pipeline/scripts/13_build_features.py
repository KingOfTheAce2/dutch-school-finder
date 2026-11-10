"""Build out/features.json from (a) the matched association lists (raw/list_matches.json),
(b) DUO fields (IB track bit, newcomer words in the location name) and (c) the website crawl checkpoint
(raw/crawl_checkpoint.jsonl). Past open days are dropped at build time. Run with `python -I`.

Envelope: {"v":1, "generated", "flags", "confidence", "schools": {DUO id: {flags, open_days, evidence, confidence}}}
 flags       sorted list of flag keys
 open_days   [{date, label, url, school_year, inferred?, shared_site?}]
 evidence    {flag: [url, snippet(<=150), "list"|"site", checked_date]}   (the best source per flag)
 confidence  {flag: "high"|"medium"|"low"}   list = high; site keyword in a relevant page = medium;
             list match at school-group level = medium; site shared by several schools = low (see README)
"""
import os, sys, re, json, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, OUT, read_jsonl, write_json_atomic

TODAY = datetime.date.today()
LISTS_DATE = "2026-10-16"

FLAGS = {
    "tto": "Bilingual secondary education (tto)",
    "tbo": "Bilingual primary education (tweetalig basisonderwijs)",
    "ib": "International Baccalaureate",
    "technasium": "Technasium",
    "montessori": "Montessori",
    "dalton": "Dalton",
    "jenaplan": "Jenaplan",
    "vrije_school": "Vrije School (Steiner/Waldorf)",
    "international": "International department or school (IGBO/IGVO, international stream)",
    "newcomer": "Newcomer class (ISK, schakelklas, taalklas, kopklas)",
}

LIST_SRC = {
    "tto": ("tto", "https://www.nuffic.nl/onderwijssectoren/voortgezet-onderwijs/tweetalig-onderwijs/alle-tto-scholen-in-nederland", "Nuffic, tto-netwerk"),
    "technasium": ("technasium", "https://www.technasium.nl/scholen/", "Stichting Technasium"),
    "montessori": ("montessori", "https://montessori.nl/professionals/vind-een-montessori-instelling/", "Nederlandse Montessori Vereniging"),
    "dalton": ("dalton", "https://dalton.nl/over-dalton/scholenzoeker/", "Nederlandse Dalton Vereniging"),
    "vrije": ("vrije_school", "https://www.vrijescholen.nl/onze-scholen", "Vereniging van vrijescholen"),
    "jenaplan": ("jenaplan", "https://jenaplan.nl/vereniging", "Nederlandse Jenaplan Vereniging"),
    "dis": ("international", "https://www.dutchinternationalschools.nl/schools/", "Dutch International Schools (DIS)"),
    "sio": ("international", "https://sio.nl/information-for-families/find-a-school-by-city/", "SIO school list"),
}
PRIORITY = ["tto", "technasium", "montessori", "dalton", "jenaplan", "vrije", "dis", "sio"]

CONCEPT = {"montessori", "dalton", "jenaplan", "vrije_school"}
NEWCOMER_NAME = re.compile(r"(?<![A-Za-z])ISK(?![A-Za-z])|internationale\s+schakelklas|nieuwkomers|taalklas|kopklas|taalschool|schakelklas\s+voor\s+nieuwkomers", re.I)


def _norm(w):
    return re.sub(r"^www\.", "", (w or "").strip().lower().rstrip("/"))


def short(s, n=150):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[:n]


def main():
    vo = json.load(open(os.path.join(OUT, "schools_vo.json"), encoding="utf-8"))
    po = json.load(open(os.path.join(OUT, "schools_po.json"), encoding="utf-8"))
    cv = {k: i for i, k in enumerate(vo["cols"])}
    cp = {k: i for i, k in enumerate(po["cols"])}
    names = {}
    for r in vo["rows"]:
        names[r[cv["id"]]] = ("vo", r[cv["name"]], r[cv["tracks"]], r[cv["web"]])
    for r in po["rows"]:
        names[r[cp["id"]]] = ("po", r[cp["name"]], 0, r[cp["web"]])

    S = collections.defaultdict(lambda: {"flags": {}, "open_days": [], "evidence": {}, "confidence": {}, "also": collections.defaultdict(set)})

    def put(sid, flag, ev, conf, src_type):
        d = S[sid]
        rank = {"high": 3, "medium": 2, "low": 1}
        d["also"][flag].add(src_type)
        if flag not in d["evidence"] or rank[conf] > rank[d["confidence"][flag]] or (
                rank[conf] == rank[d["confidence"][flag]] and src_type == "list" and d["evidence"][flag][2] != "list"):
            d["evidence"][flag] = ev
            d["confidence"][flag] = conf

    # ---- (a) association lists
    lm = json.load(open(os.path.join(RAW, "list_matches.json"), encoding="utf-8"))["matched"]
    n_list = collections.Counter()
    for sid, L in lm.items():
        for m in sorted(L, key=lambda x: PRIORITY.index(x["source"])):
            flag, url, org = LIST_SRC[m["source"]]
            e = m["entry"]
            extra = e.get("extra") or {}
            if m["source"] == "tto":
                snip = "%s: %s, %s (%s)" % (org, e["name"], e["city"], ", ".join(extra.get("levels") or []))
                if e.get("web"):
                    url = e["web"] if e["web"].startswith("http") else url
                    url = "https://www.nuffic.nl/onderwijssectoren/voortgezet-onderwijs/tweetalig-onderwijs/alle-tto-scholen-in-nederland"
            elif m["source"] == "technasium":
                url = "https://www.technasium.nl/netwerk/%s/" % extra.get("network")
                snip = "%s: %s, %s (netwerk %s)" % (org, e["name"], e["city"] or "", extra.get("network"))
            elif m["source"] == "dis":
                cats = extra.get("categories") or []
                snip = "%s: %s, %s; %s" % (org, e["name"], e["city"], ", ".join(cats))
            else:
                snip = "%s: %s, %s" % (org, e["name"], e["city"])
            conf = "medium" if m["match"].get("group") else "high"
            put(sid, flag, [url, short(snip), "list", LISTS_DATE], conf, "list")
            n_list[m["source"]] += 1
            if m["source"] == "dis" and any(c.startswith("IB") for c in (extra.get("categories") or [])):
                put(sid, "ib", [url, short("%s: %s, programmes %s" % (org, e["name"], ", ".join(c for c in extra["categories"] if c.startswith("IB")))), "list", LISTS_DATE], conf, "list")

    # ---- (b) DUO-derived
    duo_ib = duo_nc = 0
    for sid, (kind, nm, tracks, web) in names.items():
        if kind == "vo" and tracks & 512:
            put(sid, "ib", ["https://onderwijsdata.duo.nl", "DUO leerlingen VO per vestiging 2025: location has IB programme rows (DP/CP/MYP)", "list", LISTS_DATE], "high", "list")
            duo_ib += 1
        if NEWCOMER_NAME.search(nm or ""):
            put(sid, "newcomer", ["https://onderwijsdata.duo.nl", short("DUO address file, location name: " + nm), "list", LISTS_DATE], "high", "list")
            duo_nc += 1

    # ---- (c) website crawl
    recs = read_jsonl(os.path.join(RAW, "crawl_checkpoint.jsonl"))
    seen = {}
    for r in recs:           # last record per host wins
        seen[r["host"]] = r
    st = collections.Counter()
    for h, r in seen.items():
        st[r["status"]] += 1
        ids = r.get("ids") or []
        home_n = _norm(re.sub(r"^https?://", "", r.get("home") or ""))
        same = [i for i in ids if i in names and _norm(names[i][3]) == home_n]
        ids = same or ids          # a site with one sub-path per school: the record belongs to the school(s) with that URL
        shared = len(ids) >= 2      # site serves several DUO locations (school group or board site): the flag may belong to a sibling
        for sid in ids:
            for flag, v in (r.get("flags") or {}).items():
                n, na, strong = v.get("n", 0), v.get("na", 0), v.get("strong", False)
                if flag in CONCEPT:               # concept words are often just names of sibling schools in menus:
                    if not (strong or n >= 3):    # need the term in a title/heading/URL or 3+ times in running text
                        continue
                elif not (strong or n >= 1 or na >= 1):
                    continue
                if flag == "tto" and names.get(sid, ("",))[0] == "po":
                    flag = "tbo"
                menu_only = (n == 0 and not strong)
                conf = "low" if (shared or menu_only) else "medium"
                put(sid, flag, [v["url"], short(v["snip"]), "site", r["checked"]], conf, "site")
            for d in (r.get("open_days") or []):
                try:
                    dd = datetime.date.fromisoformat(d["date"])
                except ValueError:
                    continue
                if dd < TODAY:
                    continue
                o = {"date": d["date"], "label": d["label"], "url": d["url"], "school_year": d["school_year"]}
                if d.get("inferred"):
                    o["inferred"] = True
                if shared:
                    o["shared_site"] = True
                S[sid]["open_days"].append(o)

    out = {}
    for sid, d in S.items():
        od, seen_od = [], set()
        for o in sorted(d["open_days"], key=lambda x: (x["date"], x["label"])):
            k = (o["date"], o["label"])
            if k in seen_od:
                continue
            seen_od.add(k)
            od.append(o)
        if not d["evidence"] and not od:
            continue
        item = {"flags": sorted(d["evidence"]), "open_days": od[:12], "evidence": d["evidence"], "confidence": d["confidence"]}
        both = sorted(f for f, s in d["also"].items() if len(s) > 1)
        if both:
            item["corroborated"] = both
        out[sid] = item
    res = {"v": 1, "generated": TODAY.isoformat(), "flags": FLAGS,
           "confidence": {"high": "official or association list, or DUO field", "medium": "keyword on a relevant school-site page, or list match at school-group level",
                          "low": "keyword only in a menu/link, or on a site that serves several DUO locations (school group or board site): the flag may belong to a sibling location"},
           "schools": dict(sorted(out.items()))}
    write_json_atomic(os.path.join(OUT, "features.json"), res)

    # ---- summary
    cnt = collections.Counter()
    bysrc = collections.defaultdict(collections.Counter)
    for sid, it in out.items():
        for f in it["flags"]:
            cnt[f] += 1
            bysrc[f][it["evidence"][f][2] + "/" + it["confidence"][f]] += 1
    print("schools with features:", len(out), " with open days:", sum(1 for i in out.values() if i["open_days"]),
          " open days total:", sum(len(i["open_days"]) for i in out.values()))
    for f in FLAGS:
        print(" %-13s %4d  %s" % (f, cnt[f], dict(bysrc[f])))
    print("list pairs:", dict(n_list), "duo ib:", duo_ib, "duo newcomer name:", duo_nc)
    print("crawl hosts:", dict(st), "of", len(seen))
    print("size KB:", os.path.getsize(os.path.join(OUT, "features.json")) // 1024)


if __name__ == "__main__":
    main()
