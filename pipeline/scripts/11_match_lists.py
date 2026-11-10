"""Match entries of the association lists (raw/lists_parsed.json) to DUO ids in out/schools_po.json
and out/schools_vo.json. Writes raw/list_matches.json (accepted + doubtful) and
review/lists_unmatched.json / review/lists_doubtful.json.
Manual decisions on doubtful pairs live in scripts/list_overrides.json:
  {"accept": [["source","name|city", "ID"], ...], "reject": [["source","name|city","ID"], ...]}
Run with `python -I` (needs rapidfuzz)."""
import os, sys, re, json, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, OUT, DATA
from rapidfuzz import fuzz

REVIEW = os.path.join(DATA, "review")
os.makedirs(REVIEW, exist_ok=True)

STOP = set("de het een van der den voor en of op in te the of and school scholen basisschool bs obs rkbs cbs pcbs ikc kindcentrum "
           "openbare openbaar basisonderwijs primary onderwijs college lyceum scholengemeenschap sg vmbo havo vwo mavo locatie loc "
           "praktijkonderwijs atheneum gymnasium sbo so vso".split())


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def ncity(s):
    n = norm(s)
    n = n.replace(" a d ", " aan den ").replace(" a/d ", " aan den ")
    n = re.sub(r"\bhengelo ov\b", "hengelo", n)
    if n in ("den haag", "gravenhage", "s gravenhage"):
        return "s gravenhage"
    if n in ("den bosch", "s hertogenbosch"):
        return "s hertogenbosch"
    return n


def toks(s):
    return [t for t in norm(s).split() if t not in STOP]


def host(u):
    if not u:
        return None
    u = u.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = u.split("/")[0].split("?")[0].split(":")[0]
    return re.sub(r"^www\d?\.", "", u) or None


def regdom(h):
    if not h:
        return None
    p = h.split(".")
    return ".".join(p[-2:]) if len(p) >= 2 else h


def load(name):
    d = json.load(open(os.path.join(OUT, name), encoding="utf-8"))
    c = {k: i for i, k in enumerate(d["cols"])}
    rows = []
    for r in d["rows"]:
        rows.append({"id": r[c["id"]], "name": r[c["name"]], "pc": r[c["pc"]], "city": r[c["city"]],
                     "mun": r[c["mun"]], "web": r[c["web"]], "addr": r[c["addr"]], "tracks": r[c["tracks"]] if "tracks" in c else 0})
    return rows


def build_index(rows):
    by_pc6, by_pc4, by_city, by_host = {}, {}, {}, {}
    for s in rows:
        s["_n"] = norm(s["name"]); s["_t"] = toks(s["name"]); s["_h"] = host(s["web"])
        by_pc6.setdefault(s["pc"], []).append(s)
        by_pc4.setdefault((s["pc"] or "")[:4], []).append(s)
        by_city.setdefault(ncity(s["city"]), []).append(s)
        by_city.setdefault(ncity(s["mun"]), []).append(s)
        if s["_h"]:
            by_host.setdefault(s["_h"], []).append(s)
    return by_pc6, by_pc4, by_city, by_host


def nscore(a, b_norm, b_toks, a_toks):
    """Name similarity 0-100, tolerant to extra words on either side."""
    if not a_toks or not b_toks:
        return 0
    s1 = fuzz.token_set_ratio(" ".join(a_toks), " ".join(b_toks))
    s2 = fuzz.partial_ratio(" ".join(a_toks), " ".join(b_toks)) if min(len(" ".join(a_toks)), len(" ".join(b_toks))) >= 6 else 0
    return max(s1 * 0.95, s2 * 0.9)


def match_entry(e, idx, pool_label):
    by_pc6, by_pc4, by_city, by_host = idx
    et = toks(e["name"])
    en = norm(e["name"])
    eh = host(e["web"])
    cands = {}

    def add(s, why):
        c = cands.setdefault(s["id"], {"s": s, "why": set()})
        c["why"].add(why)

    if e["pc"]:
        for s in by_pc6.get(e["pc"], []):
            add(s, "pc6")
        for s in by_pc4.get(e["pc"][:4], []):
            add(s, "pc4")
    if eh:
        for s in by_host.get(eh, []):
            add(s, "host")
    cn = ncity(e["city"])
    if cn:
        for s in by_city.get(cn, []):
            add(s, "city")
    out = []
    for c in cands.values():
        s = c["s"]
        ctoks = set(norm(e["city"]).split()) | set(norm(s["city"]).split())
        et_ = [t for t in et if t not in ctoks] or et
        st_ = [t for t in s["_t"] if t not in ctoks] or s["_t"]
        sc = nscore(en, s["_n"], st_, et_)
        why = c["why"]
        samehost = "host" in why
        regdom_eq = bool(eh and s["_h"] and regdom(eh) == regdom(s["_h"]))
        # grading
        grade = None
        haspc = bool(e["pc"])
        if haspc:
            if "pc6" in why and (sc >= 72 or (samehost and sc >= 20)):
                grade = "high"
            elif "pc6" in why and sc >= 45:
                grade = "doubtful"
            elif samehost and sc >= 60 and "pc4" in why:
                grade = "high"
            elif samehost and sc >= 60 and "city" in why:
                grade = "high"
            elif regdom_eq and "city" in why and sc >= 60:
                grade = "high"
            elif "pc4" in why and sc >= 88:
                grade = "high"
            elif samehost and "city" in why and sc >= 30:
                grade = "doubtful"
            elif ("pc4" in why or "city" in why) and sc >= 80:
                grade = "doubtful"
        else:
            if samehost and "city" in why:
                grade = "high"
            elif "city" in why and sc >= 90:
                grade = "high"
            elif "city" in why and sc >= 78:
                grade = "doubtful"
            elif samehost and sc >= 60:
                grade = "doubtful"
        if grade:
            out.append({"id": s["id"], "grade": grade, "score": round(sc, 1), "why": sorted(why), "school": s["name"],
                        "city": s["city"], "pc": s["pc"]})
    out.sort(key=lambda x: (x["grade"] != "high", -x["score"]))
    return out


TTO_BITS = {"tvwo": 64 | 128 | 256, "thavo": 32, "tvmbo": 2 | 4 | 8 | 16, "tmavo": 16, "tgymnasium": 128, "tatheneum": 256}


# which DUO file(s) each source can match, per entry
def pools_for(src, e):
    if src in ("tto", "technasium"):
        return ["vo"]
    if src == "vrije":
        t = e["extra"].get("type") or ""
        if t.startswith("voortgezet") or t.startswith("initiatief-voortgezet"):
            return ["vo"]
        if t.startswith("primair") or t.startswith("initiatief-primair") or t.startswith("speciaal"):
            return ["po"]
        return []
    return ["po", "vo"]


def main():
    parsed = json.load(open(os.path.join(RAW, "lists_parsed.json"), encoding="utf-8"))
    rows = {"po": load("schools_po.json"), "vo": load("schools_vo.json")}
    idx = {k: build_index(v) for k, v in rows.items()}
    ov_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "list_overrides.json")
    ov = json.load(open(ov_path, encoding="utf-8")) if os.path.exists(ov_path) else {"accept": [], "reject": []}
    acc = {(a[0], norm(a[1]), a[2]) for a in ov["accept"]}
    rej = {(a[0], norm(a[1]), a[2]) for a in ov["reject"]}
    result = {"matched": {}, "doubtful": [], "unmatched": [], "stats": {}}
    for src, entries in parsed.items():
        st = {"entries": 0, "matched": 0, "doubtful": 0, "unmatched": 0, "skipped_nonschool": 0}
        for e in entries:
            key = norm("%s|%s" % (e["name"], e["city"]))
            pools = pools_for(src, e)
            if not pools:
                st["skipped_nonschool"] += 1
                continue
            st["entries"] += 1
            allc = []
            for p in pools:
                for c in match_entry(e, idx[p], p):
                    c["pool"] = p
                    allc.append(c)
            allc = [c for c in allc if (src, key, c["id"]) not in rej]
            if src == "technasium":      # technasium needs havo/vwo: drop praktijkonderwijs-only and vmbo-only locations
                tr = {r_["id"]: r_["tracks"] for r_ in rows["vo"]}
                allc = [c for c in allc if not tr.get(c["id"]) or tr[c["id"]] & (32 | 64 | 128 | 256)]
            if src == "tto":
                req = 0
                for lv in e["extra"].get("levels") or []:
                    req |= TTO_BITS.get(lv, 0)
                if req:
                    tr = {r_["id"]: r_["tracks"] for r_ in rows["vo"]}
                    allc = [c for c in allc if not tr.get(c["id"]) or tr[c["id"]] & req]
            have = {c["id"] for c in allc}
            for (a_src, a_key, a_id) in acc:
                if a_src == src and a_key == key and a_id not in have:
                    for p in pools:
                        for r_ in rows[p]:
                            if r_["id"] == a_id:
                                allc.append({"id": a_id, "grade": "doubtful", "score": 0, "why": [], "school": r_["name"],
                                             "city": r_["city"], "pc": r_["pc"], "pool": p})
            for c in allc:
                if (src, key, c["id"]) in acc:
                    c["grade"] = "high"; c["why"].append("manual")
            highs = [c for c in allc if c["grade"] == "high"]
            if e["pc"] and any("pc6" in c["why"] for c in highs):
                highs = [c for c in highs if "pc6" in c["why"]]
            if not e["pc"] and len(highs) > 1:
                best = highs[0]
                second = highs[1]
                if best["score"] >= 60 and best["score"] - second["score"] >= 15:
                    highs = [best]
                else:
                    highs = [c for c in highs if c["score"] >= best["score"] - 15] or [best]
                    if len(highs) > 1:
                        for c in highs:
                            c["group"] = True
            if highs:
                # keep best; also keep other highs sharing the same top score within 3 points (multi-location schools)
                top = highs[0]["score"]
                # same-host / same-pc6 ties are all kept; otherwise only close scores
                keep = [c for c in highs if c["score"] >= top - 3 or "host" in c["why"] or "pc6" in c["why"]][:6]
                for c in keep:
                    result["matched"].setdefault(c["id"], []).append({"source": src, "entry": e, "match": c})
                st["matched"] += 1
            else:
                dbt = [c for c in allc if c["grade"] == "doubtful"][:3]
                if dbt:
                    result["doubtful"].append({"source": src, "entry": e, "cands": dbt})
                    st["doubtful"] += 1
                else:
                    result["unmatched"].append({"source": src, "entry": e})
                    st["unmatched"] += 1
        result["stats"][src] = st
    json.dump(result, open(os.path.join(RAW, "list_matches.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(result["unmatched"], open(os.path.join(REVIEW, "lists_unmatched.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(result["doubtful"], open(os.path.join(REVIEW, "lists_doubtful.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in result["stats"].items():
        print(k, v)


if __name__ == "__main__":
    main()
