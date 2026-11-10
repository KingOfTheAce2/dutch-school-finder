"""Step 9: sanity checks and coverage report (prints; no files written)."""
import collections, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT

SPOT = [  # (file, name substring, city substring) - eyeball coordinates and tracks
    ("vo", "Vossius", "Amsterdam"), ("vo", "Stedelijk Gymnasium", "Utrecht"),
    ("vo", "Praedinius", "Groningen"), ("vo", "Bonnefanten", "Maastricht"),
    ("vo", "Maartens", "Maastricht"), ("po", "Maasparel", "Stevensweert"),
]


def load(n):
    with open(os.path.join(OUT, n), encoding="utf-8") as f:
        return json.load(f)


def rec(d, r):
    return dict(zip(d["cols"], r))


def km(a, b, c, d):
    return math.hypot((a - c) * 111.2, (b - d) * 68.0)


def pct(a, b):
    return "%d/%d (%.1f%%)" % (a, b, 100.0 * a / b) if b else "0/0"


def check_detail():
    """Coverage and consistency checks for detail_po / detail_vo / inspection. Raises SystemExit on a hard failure."""
    errs = []
    po, vo = load("schools_po.json"), load("schools_vo.json")
    ids_po, ids_vo = {r[0] for r in po["rows"]}, {r[0] for r in vo["rows"]}
    dp, dv, ins = load("detail_po.json"), load("detail_vo.json"), load("inspection.json")
    so = load("schools_so.json")
    rs = [rec(so, r) for r in so["rows"]]
    ids_so = {r["id"] for r in rs}
    print("\n==== schools_so.json: %d rows | type %s | cluster %s" % (
        len(rs), dict(collections.Counter(r["so_type"] for r in rs)), dict(collections.Counter(r["cl"] for r in rs))))
    print("  geo %s | with pupils %s | with website %s" % (
        dict(collections.Counter(r["g"] for r in rs)), pct(sum(1 for r in rs if r["pupils"] is not None), len(rs)),
        pct(sum(1 for r in rs if r["web"]), len(rs))))
    if len(ids_so) != len(rs) or ids_so & ids_po:
        errs.append("schools_so ids not unique / overlap with schools_po")
    for r in rs:
        if r["so_type"] not in ("SO", "VSO", "SO/VSO") or r["cl"] not in (1, 2, 3, 4, None):
            errs.append("so invalid type/cluster " + r["id"])
        if r["lat"] is not None and not (50.7 < r["lat"] < 53.7 and 3.2 < r["lon"] < 7.3):
            errs.append("so outside NL " + r["id"])
        if r["pupils"] is not None and r["pupils"] < 0:
            errs.append("so pupils invalid " + r["id"])
    print("\n==== detail_po.json (%d schools with data of %d)" % (len(dp["schools"]), len(ids_po)))
    S = dp["schools"]
    for f in ("pt", "es", "dm", "at", "lj", "rn", "hv"):
        print("  %-3s %s" % (f, pct(sum(1 for d in S.values() if f in d), len(ids_po))))
    print("  pt with a 2025 value: %s" % pct(sum(1 for d in S.values() if any(x[0] == 2025 and x[1] is not None for x in d.get("pt", []))), len(ids_po)))
    for i, d in S.items():
        if i not in ids_po:
            errs.append("detail_po id not in schools_po: " + i)
        for t, avg, n in d.get("es", []):
            if n is None or n < 5 or avg is None:
                errs.append("es below 5 or null " + i)
        if "dm" in d and (d["dm"][2] < 5 or d["dm"][0] < 0):
            errs.append("dm invalid " + i)
        for y, n, s_, sh in d.get("at", []):
            if sh is not None and abs(sum(x for x in sh if x is not None) - 100) > 0.6:
                errs.append("advice shares not 100 %s %s" % (i, y))
        for k, (p1, p2, n) in d.get("rn", {}).items():
            if n < 5 or any(x is not None and not 0 <= x <= 100 for x in (p1, p2)) or (p1 is not None and p2 is not None and p2 > p1 + 0.05):
                errs.append("rn invalid %s %s" % (i, k))
        if "hv" in d and (d["hv"][2] < 5 or any(x is not None and x < 0 for x in d["hv"])):
            errs.append("hv invalid " + i)
        if "lj" in d and (len(d["lj"]) != 8 or any(x is not None and (x < 0 or 1 <= x <= 4) for x in d["lj"])):
            errs.append("lj invalid " + i)
    print("\n==== detail_vo.json (%d schools with data of %d)" % (len(dv["schools"]), len(ids_vo)))
    V = dv["schools"]
    for f in ("pt", "tp", "pr", "cm", "ce", "zb", "ov", "op"):
        print("  %-3s %s" % (f, pct(sum(1 for d in V.values() if f in d), len(ids_vo))))
    for i, d in V.items():
        if i not in ids_vo:
            errs.append("detail_vo id not in schools_vo: " + i)
        for lab, lst in d.get("pr", {}).items():
            for pr_ in lst:
                if (pr_[1] is None) != (pr_[2] is None) or (pr_[1] is not None and (pr_[1] < 5 or not 0 <= pr_[2] <= 100)):
                    errs.append("pr invalid %s %s %s" % (i, lab, pr_))
        for lab, lst in d.get("ce", {}).items():
            for y, m_, n, *_ in lst:
                if n < 5 or not 1.0 <= m_ <= 10.0:
                    errs.append("ce invalid %s %s %s" % (i, lab, [y, m_, n]))
        if "zb" in d and (d["zb"][0] is None or d["zb"][0] < 5):
            errs.append("zb invalid " + i)
        for pc4_, n, *_ in d.get("cm", []):
            if n < 5:
                errs.append("cm below 5 " + i)
    print("\n==== inspection.json: %d schools, as_of %s, licence %s" % (len(ins["schools"]), ins["as_of"], ins["licence"]))
    RATED = ("Goed", "Voldoende", "Onvoldoende", "Zwak", "Zeer zwak")
    allids = len(ids_po) + len(ids_so) + len(ids_vo)
    print("  listed schools: %s | counts %s" % (pct(len(ins["schools"]), allids), ins["counts"]))
    rated = {i: s for i, s in ins["schools"].items() if s["o"] in RATED}
    print("  rated: %s | with standards st/xs: %s | with bestuur b: %s" % (
        pct(len(rated), allids), pct(sum(1 for s in rated.values() if "st" in s or "xs" in s), len(rated)),
        pct(sum(1 for s in ins["schools"].values() if "b" in s), len(ins["schools"]))))
    if ins["counts"]["rated"] != len(rated):
        errs.append("inspection counts.rated does not match")
    for i, s in ins["schools"].items():
        if i not in ids_po and i not in ids_vo and i not in ids_so:
            errs.append("inspection id unknown " + i)
        if s["o"] in RATED and not s.get("d"):
            errs.append("rated without date " + i)
        if s["o"] not in RATED and s["o"] not in ("Geen eindoordeel", "Basistoezicht"):
            errs.append("inspection unknown o %s %s" % (i, s["o"]))
        if s["o"] == "Geen eindoordeel" and ("d" in s or "st" in s):
            errs.append("unrated school with details " + i)
        for code in list(s.get("st", {})) + [c for v_ in s.get("xs", {}).values() for c in v_]:
            if code in ("OP0", "OP1", "OP2", "OP3", "OP4", "OP5", "OP6", "VS1", "VS2", "OR1", "OR2", "SKA1", "SKA2", "SKA3") and code not in ins["labels"]:
                errs.append("no label for " + code)
    print("\n---- detail spot checks")
    for f, nm, city in (("vo", "Vossius", "Amsterdam"), ("vo", "Stedelijk Gymnasium", "Utrecht"), ("po", "Maasparel", "Stevensweert")):
        d = load("schools_%s.json" % f)
        D = S if f == "po" else V
        hit = [rec(d, r) for r in d["rows"] if nm.lower() in r[1].lower() and city.lower() in (r[4] + r[5]).lower()]
        if not hit:
            errs.append("spot check school not found: " + nm)
        for r in hit[:1]:
            x = D.get(r["id"])
            print(" ", f, r["id"], r["name"], "->", json.dumps(x, separators=(",", ":"))[:700] if x else "NO DETAIL")
            if not x or "pt" not in x:
                errs.append("spot check without pt: " + nm)
            if f == "vo" and x and "pr" not in x:
                errs.append("spot check VO without pass rates: " + nm)
            if ins["schools"].get(r["id"]):
                print("    inspection:", ins["schools"][r["id"]])
    if len(S) < 0.9 * len(ids_po) or len(V) < 0.85 * len(ids_vo):
        errs.append("detail coverage too low")
    if errs:
        print("\nDETAIL CHECK FAILURES:", len(errs))
        for e in errs[:30]:
            print("  ", e)
        raise SystemExit(1)
    print("\ndetail checks OK")


def main():
    pc4 = load("pc4.json")
    for name in ("po", "vo"):
        d = load("schools_%s.json" % name)
        recs = [rec(d, r) for r in d["rows"]]
        print("\n==== %s: %d rows" % (name.upper(), len(recs)))
        print("per province:", dict(sorted(collections.Counter(d["prov"][r["prov"]] if r["prov"] >= 0 else "?" for r in recs).items())))
        print("geo quality:", dict(collections.Counter(r["g"] for r in recs)))
        bad = [r for r in recs if r["lat"] is not None and not (50.7 < r["lat"] < 53.7 and 3.2 < r["lon"] < 7.3)]
        print("outside NL bbox:", len(bad), [(r["id"], r["name"]) for r in bad[:5]])
        far = []
        for r in recs:
            c = pc4.get(r["pc"][:4])
            if r["lat"] is not None and r["g"] == 0 and c and km(r["lat"], r["lon"], c[0], c[1]) > 12:
                far.append((r["id"], r["name"], r["pc"], round(km(r["lat"], r["lon"], c[0], c[1]), 1)))
        print("address hit >12 km from its PC4 centroid:", len(far), far[:6])
        print("without pupils:", sum(1 for r in recs if r["pupils"] is None), "| with website:", sum(1 for r in recs if r["web"]))
        if name == "po":
            n_adv = sum(1 for r in recs if r["adv"] and r["adv"][0] > 0)
            full = sum(1 for r in recs if r["adv"] and r["adv"][0] > 0 and r["adv"][1] == 0)
            print("with advice data (n>0): %d (%.1f%%); with no suppressed cell: %d (%.1f%%); sbo: %d" % (
                n_adv, 100 * n_adv / len(recs), full, 100 * full / len(recs), sum(r["sbo"] for r in recs)))
        else:
            n_ex = sum(1 for r in recs if r["exam"] and any(x[1] for x in r["exam"]))
            print("with exam data (>=1 track): %d (%.1f%%)" % (n_ex, 100 * n_ex / len(recs)))
            print("with tracks known:", sum(1 for r in recs if r["tracks"]))
    print("\n==== spot checks")
    for f, nm, city in SPOT:
        d = load("schools_%s.json" % f)
        hits = [rec(d, r) for r in d["rows"] if nm.lower() in r[1].lower() and city.lower() in (r[4] + r[5]).lower()]
        for r in hits[:3]:
            tr = ""
            if f == "vo":
                tr = [k for k, b in d["bits"].items() if r["tracks"] & b]
            print(f, r["id"], r["name"], "|", r["addr"], r["pc"], r["city"], "|", r["lat"], r["lon"], "g=%d" % r["g"],
                  "|", "pupils", r["pupils"], tr, (r.get("exam") or ""))
        if not hits:
            print(f, nm, city, "-> NO MATCH")
    check_detail()


if __name__ == "__main__":
    main()
