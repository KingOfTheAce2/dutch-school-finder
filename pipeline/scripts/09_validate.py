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


if __name__ == "__main__":
    main()
