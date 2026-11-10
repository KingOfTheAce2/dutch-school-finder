"""Step 5b: build out/schools_so.json (speciaal onderwijs SO and voortgezet speciaal onderwijs VSO).

Sources (DUO): "alle vestigingen sbo, so en vso" (universe, address, denomination, website, CLUSTER, ONDERWIJS) and
"leerlingen po naar soort po, cluster en leeftijd" 2025-2026 (pupils per vestiging and type on 1 October 2025).
Same envelope and columns as schools_po.json, plus so_type, cl, cls, pso, pvso. SBAO (sbo = 1) stays in schools_po.json.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, SO_PUPIL_FILE, write_json_atomic
import duo
from geo import Geo


def cell(v):
    v = (v or "").strip()
    return int(v) if v.isdigit() else None


def main():
    schools = duo.load_so_schools()
    pup = duo.read_csv_auto(SO_PUPIL_FILE)
    geo = Geo()
    geo.learn_gemeente_names([pup])
    ages = [k for k in pup[0] if k.startswith("LEEFTIJD_")]
    pupils = {}   # id -> {"So": [sum, any suppressed], "Vso": [...]}
    for r in pup:
        kind = r["SOORT_PO"].strip()
        if kind not in ("So", "Vso"):
            continue
        p = pupils.setdefault(r["INSTELLINGSCODE"].strip() + r["VESTIGINGSCODE"].strip(), {}).setdefault(kind, [0, 0])
        for a in ages:
            v = cell(r[a])
            if v is None:
                p[1] = 1
            else:
                p[0] += v
    dens = sorted({s["den"] for s in schools})
    rows = []
    for s in sorted(schools, key=lambda x: x["id"]):
        lat, lon, q, mun, city = geo.resolve(s)
        p = pupils.get(s["id"])
        addr = (s["street"] + " " + s["hn_raw"]).strip()
        cl = s["clusters"]
        tot = lb = pso = pvso = None
        if p:
            tot = sum(v[0] for v in p.values())
            lb = int(any(v[1] for v in p.values()))
            pso = p["So"][0] if "So" in p else None
            pvso = p["Vso"][0] if "Vso" in p else None
        rows.append([
            s["id"], s["name"], addr, s["pc6"], city, mun, lat, lon, q, s["prov"],
            dens.index(s["den"]), 0, tot, lb, None, s["web"] or None,
            s["so_type"], cl[0] if len(cl) == 1 else None, cl or None, pso, pvso,
        ])
    out = {
        "v": 1,
        "years": {"pupils": "2025-2026 (peildatum 2025-10-01)"},
        "cols": ["id", "name", "addr", "pc", "city", "mun", "lat", "lon", "g", "prov", "den", "sbo",
                 "pupils", "pupils_lb", "adv", "web", "so_type", "cl", "cls", "pso", "pvso"],
        "prov": duo.PROVINCES,
        "den": dens,
        "levels": [],
        "clusters": {"1": "visual impairment", "2": "hearing impairment and severe speech/language disorders",
                     "3": "physical or intellectual disability, long-term illness", "4": "behavioural or psychiatric problems"},
        "rows": rows,
    }
    write_json_atomic(os.path.join(OUT, "schools_so.json"), out)
    print("schools_so.json rows:", len(rows), "| with pupils:", sum(1 for r in rows if r[12] is not None))


if __name__ == "__main__":
    main()
