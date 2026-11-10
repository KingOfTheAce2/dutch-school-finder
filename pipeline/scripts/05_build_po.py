"""Step 5: build out/schools_po.json (primary + speciaal basisonderwijs).

Sources (DUO): address files (universe + address/denomination/website), pupils per vestiging
2025-2026 (peildatum 2025-10-01), schooladviezen 2024-2025 (leavers of school year 2024/25).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, PO_PUPIL_FILE, PO_ADVICE_FILE, write_json_atomic
import duo
from geo import Geo

LEVELS = ["VSO", "PRO", "VMBO_B", "VMBO_B_K", "VMBO_K", "VMBO_K_GT", "VMBO_GT", "VMBO_GT_HAVO",
          "HAVO", "HAVO_VWO", "VWO", "ADVIES_NIET_MOGELIJK"]


def cell(v):
    v = (v or "").strip()
    if v.isdigit():
        return int(v)
    return None  # "<5" (suppressed) or anything unexpected


def main():
    schools = duo.load_po_schools()
    pup = duo.read_csv(PO_PUPIL_FILE, "utf-8-sig")
    adv = duo.read_csv(PO_ADVICE_FILE, "utf-8-sig")
    geo = Geo()
    geo.learn_gemeente_names([pup, adv])

    pupils = {}  # id -> [sum of exact cells, any suppressed cell]
    for r in pup:
        i = r["INSTELLINGSCODE"].strip() + r["VESTIGINGSCODE"].strip()
        p = pupils.setdefault(i, [0, 0])
        for y in range(1, 9):
            v = cell(r["LEERJAAR_%d" % y])
            if v is None:
                p[1] = 1
            else:
                p[0] += v

    advice = {}
    for r in adv:
        i = r["INSTELLINGSCODE"].strip() + r["VESTIGINGSCODE"].strip()
        vals = [cell(r[l]) for l in LEVELS]
        n = sum(v for v in vals if v is not None)
        s = sum(1 for v in vals if v is None)
        shares = None
        if n > 0:
            shares = [None if v is None else round(100.0 * v / n, 1) for v in vals]
        advice[i] = [n, s, shares]

    dens = sorted({s["den"] for s in schools})
    rows = []
    for s in sorted(schools, key=lambda x: x["id"]):
        lat, lon, q, mun, city = geo.resolve(s)
        p = pupils.get(s["id"])
        addr = (s["street"] + " " + s["hn_raw"]).strip()
        rows.append([
            s["id"], s["name"], addr, s["pc6"], city, mun, lat, lon, q, s["prov"],
            dens.index(s["den"]), s["sbo"],
            p[0] if p else None, p[1] if p else None,
            advice.get(s["id"]), s["web"] or None,
        ])
    out = {
        "v": 1,
        "years": {"pupils": "2025-2026 (peildatum 2025-10-01)", "advice": "2024-2025 (leavers, peildatum 2024-10-01)"},
        "cols": ["id", "name", "addr", "pc", "city", "mun", "lat", "lon", "g", "prov", "den", "sbo",
                 "pupils", "pupils_lb", "adv", "web"],
        "prov": duo.PROVINCES,
        "den": dens,
        "levels": LEVELS,
        "rows": rows,
    }
    write_json_atomic(os.path.join(OUT, "schools_po.json"), out)
    print("schools_po.json rows:", len(rows))


if __name__ == "__main__":
    main()
