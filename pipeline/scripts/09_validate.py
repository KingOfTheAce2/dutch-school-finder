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
    print("\n==== detail_po.json (%d schools with data of %d)" % (len(dp["schools"]), len(ids_po)))
    S = dp["schools"]
    for f in ("pt", "es", "dm", "at"):
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
    print("\n==== detail_vo.json (%d schools with data of %d)" % (len(dv["schools"]), len(ids_vo)))
    V = dv["schools"]
    for f in ("pt", "tp", "pr", "cm"):
        print("  %-3s %s" % (f, pct(sum(1 for d in V.values() if f in d), len(ids_vo))))
    for i, d in V.items():
        if i not in ids_vo:
            errs.append("detail_vo id not in schools_vo: " + i)
        for lab, lst in d.get("pr", {}).items():
            for pr_ in lst:
                if (pr_[1] is None) != (pr_[2] is None) or (pr_[1] is not None and (pr_[1] < 5 or not 0 <= pr_[2] <= 100)):
                    errs.append("pr invalid %s %s %s" % (i, lab, pr_))
        for pc4_, n, *_ in d.get("cm", []):
            if n < 5:
                errs.append("cm below 5 " + i)
    print("\n==== inspection.json: %d schools, as_of %s, licence %s" % (len(ins["schools"]), ins["as_of"], ins["licence"]))
    print("  coverage of po+vo schools: %s" % pct(len(ins["schools"]), len(ids_po) + len(ids_vo)))
    for i in ins["schools"]:
        if i not in ids_po and i not in ids_vo:
            errs.append("inspection id unknown " + i)
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
