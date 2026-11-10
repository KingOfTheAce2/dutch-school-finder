"""Step 8: build out/meta.json (data years, generation date, counts, match rates, attribution lines)."""
import datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, OUT, read_jsonl, write_json_atomic


def load(n):
    with open(os.path.join(OUT, n), encoding="utf-8") as f:
        return json.load(f)


def main():
    po, vo, pc4 = load("schools_po.json"), load("schools_vo.json"), load("pc4.json")
    gi_po, gi_vo = po["cols"].index("g"), vo["cols"].index("g")
    cache = {r["k"]: r for r in read_jsonl(os.path.join(RAW, "geocode_cache.jsonl")) if "k" in r}
    addr = [r for k, r in cache.items() if not k.startswith("pc6|")]
    addr_ok = sum(1 for r in addr if r["s"] == "ok")
    addr_exact_suffix = sum(1 for r in addr if r["s"] == "ok" and r.get("x"))

    def q(rows, gi):
        c = {0: 0, 1: 0, 2: 0, 3: 0}
        for r in rows:
            c[r[gi]] += 1
        return {"address": c[0], "pc6_centroid": c[1], "pc4_centroid": c[2], "none": c[3]}

    meta = {
        "generated": datetime.date.today().isoformat(),
        "data_years": {
            "po_pupils": po["years"]["pupils"],
            "po_advice": po["years"]["advice"],
            "vo_pupils": vo["years"]["pupils"],
            "vo_exams": vo["years"]["exams"],
            "pc4_geometry": "CBS postcode4, jaarcode 2024 (PDOK OGC API)",
            "addresses": "DUO address files, retrieved " + datetime.date.today().isoformat(),
        },
        "counts": {
            "schools_po": len(po["rows"]),
            "schools_po_sbo": sum(1 for r in po["rows"] if r[po["cols"].index("sbo")]),
            "schools_vo": len(vo["rows"]),
            "pc4": len(pc4),
        },
        "geocoding": {
            "address_keys": len(addr),
            "address_matched": addr_ok,
            "address_match_rate": round(addr_ok / len(addr), 4) if addr else None,
            "address_matched_incl_suffix": addr_exact_suffix,
            "quality_codes": {"0": "BAG address via PDOK Locatieserver", "1": "PC6 centroid fallback",
                              "2": "PC4 centroid fallback", "3": "no coordinates"},
            "po": q(po["rows"], gi_po),
            "vo": q(vo["rows"], gi_vo),
        },
        "attribution": [
            {"source": "DUO Open Onderwijsdata",
             "text": "School addresses, pupil numbers, schooladviezen and exam results: DUO (Dienst Uitvoering Onderwijs), "
                     "Open Onderwijsdata, https://duo.nl/open_onderwijsdata. We selected, joined and calculated "
                     "percentages from the original files.",
             "licence": "CC BY 4.0 (DUO's own site also states CC0 1.0; we apply the stricter CC BY 4.0)",
             "licence_url": "https://creativecommons.org/licenses/by/4.0/",
             "url": "https://onderwijsdata.duo.nl"},
            {"source": "CBS",
             "text": "Postcode (PC4) areas: CBS (Statistics Netherlands), dataset CBS Postcode4 statistics, "
                     "distributed via PDOK. Centroids computed by us.",
             "licence": "CC BY 4.0",
             "licence_url": "https://creativecommons.org/licenses/by/4.0/",
             "url": "https://api.pdok.nl/cbs/postcode4/ogc/v1"},
            {"source": "Kadaster / PDOK",
             "text": "Address coordinates and municipality names: Kadaster, BAG (Basisregistratie Adressen en Gebouwen) "
                     "via the PDOK Locatieserver. Source: Kadaster / PDOK.",
             "licence": "BAG is published as open data (Public Domain Mark 1.0 per data.overheid.nl); "
                        "credited here under CC BY 4.0 terms as a precaution",
             "licence_url": "https://creativecommons.org/licenses/by/4.0/",
             "url": "https://www.pdok.nl/ogc-apis/-/article/pdok-locatieserver"},
        ],
        "disclaimer": "Not affiliated with, or endorsed by, DUO, CBS, Kadaster or PDOK. DUO hides counts below 5 "
                      "(shown as null); shares and pass rates computed from partial data are flagged.",
    }
    old_path = os.path.join(OUT, "meta.json")
    if os.path.exists(old_path):           # keep the features block written by 14_features_meta.py
        try:
            prev = json.load(open(old_path, encoding="utf-8"))
            if "features" in prev:
                meta["features"] = prev["features"]
        except ValueError:
            pass
    write_json_atomic(os.path.join(OUT, "meta.json"), meta)
    print("meta.json written; address match rate", meta["geocoding"]["address_match_rate"])


if __name__ == "__main__":
    main()
