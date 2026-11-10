"""Step 6: build out/schools_vo.json (voortgezet onderwijs).

Sources (DUO): address file (universe), pupils per vestiging naar onderwijstype 2025 (peildatum 2025-10-01,
provisional), exam results 2024-2025 (geslaagden/gezakten per vestiging, onderwijstype, leerweg, afdeling).
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, VO_PUPIL_FILE, VO_EXAM_FILE, write_json_atomic
import duo
from geo import Geo

# track bit flags (documented in README.md)
BIT = {"pro": 1, "bb": 2, "kb": 4, "gl": 8, "tl": 16, "havo": 32, "vwo": 64, "gym": 128, "ath": 256,
       "ib": 512, "ess": 1024}
TRACK_ORDER = ["pro", "bb", "kb", "gl", "tl", "havo", "vwo"]
TYPE_COL = "ONDERWIJSTYPE VO EN LEER- OF VERBLIJFSJAAR"

TYPE_MAP = {
    "Praktijkonderwijs alle vj": ["pro"],
    "VMBO BL lj 3-4": ["bb"],
    "VMBO KL lj 3-4": ["kb"],
    "VMBO GL lj 3-4": ["gl"],
    "VMBO TL lj 3-4": ["tl"],
    "HAVO lj 4-5": ["havo"],
    "VWO lj 4-6": ["vwo"],
}


def cell(v):
    v = (v or "").strip()
    return int(v) if v.isdigit() else None


def tracks_from_row(t, name):
    """Track flags a (non-empty) pupil row proves are offered at the location."""
    up = name.upper()
    if t.endswith("uitbest. aan VAVO"):
        return []
    out = list(TYPE_MAP.get(t, []))
    if t in ("Brugjaar 1-2", "HAVO/VWO lj 3"):
        toks = set(re.findall(r"\b(BB|KB|GL|TL|HAVO|VWO)\b", re.sub(r"[/\-]", " ", up)))
        if "MAVO" in up:
            toks |= {"TL", "GL"}
        out += [x.lower() for x in toks]
    if "VWO" in out or t.startswith("VWO") or "VWO" in up:
        if "GYMNASIUM" in up or re.search(r"\bGYM\b", up.replace("-", " ")):
            out.append("gym")
        if "ATHENEUM" in up or re.search(r"\bATH\b", up.replace("-", " ")):
            out.append("ath")
    if "BACCALAUREATE" in up or t == "Int. Baccelaureaat":
        out.append("ib")
    if t == "European Secondary School" or "EUROPEAN SECONDARY SCHOOL" in up:
        out.append("ess")
    return out


def exam_track(typ, leerweg):
    typ, leerweg = typ.strip().upper(), leerweg.strip().upper()
    if typ == "HAVO":
        return "havo"
    if typ == "VWO":
        return "vwo"
    if typ == "VMBO":
        return {"BL": "bb", "KL": "kb", "GL": "gl", "TL": "tl"}.get(leerweg)
    return None


def main():
    schools = duo.load_vo_schools()
    pup = duo.read_csv(VO_PUPIL_FILE, "utf-8-sig")
    exa = duo.read_csv(VO_EXAM_FILE, "utf-8-sig")
    geo = Geo()
    geo.learn_gemeente_names([exa])
    # also use the primary files, which carry mixed-case municipality names for the same GEMEENTENUMMER
    geo.learn_gemeente_names([duo.read_csv("bo_leerlingen_2025-2026.csv", "utf-8-sig")])

    cols = [c for c in pup[0] if c.startswith("LEER- OF VERBLIJFSJAAR")]
    mask, pupils = {}, {}
    for r in pup:
        i = r["INSTELLINGSCODE"].strip() + r["VESTIGINGSCODE"].strip()
        t = r[TYPE_COL].strip()
        if t.endswith("uitbest. aan VAVO"):
            continue
        vals = [cell(r[c]) for c in cols]
        tot = sum(v for v in vals if v is not None)
        supp = any(v is None for v in vals)
        p = pupils.setdefault(i, [0, 0])
        p[0] += tot
        p[1] |= 1 if supp else 0
        if tot > 0 or supp:
            m = mask.get(i, 0)
            for tr in tracks_from_row(t, r["OPLEIDINGSNAAM"]):
                m |= BIT[tr]
            mask[i] = m

    # exam results: aggregate afdelingen/sectors to one record per (vestiging, track)
    agg = {}
    for r in exa:
        tr = exam_track(r["ONDERWIJSTYPE VO"], r["LEERWEG VMBO"])
        if not tr:
            continue
        i = r["VESTIGINGSCODE"].strip()
        a = agg.setdefault((i, tr), [0, 0, 0])  # cand, passed, suppressed rows
        c, g = cell(r["EXAMENKANDIDATEN"]), cell(r["GESLAAGDEN"])
        if c is None or g is None:
            a[2] += 1
        else:
            a[0] += c
            a[1] += g
    exam = {}
    for (i, tr), (c, g, sp) in agg.items():
        if c > 0:
            rec = [tr, c, round(100.0 * g / c, 1), 1 if sp else 0]
        else:
            rec = [tr, None, None, 0]
        exam.setdefault(i, []).append(rec)
    for i in exam:
        exam[i].sort(key=lambda x: TRACK_ORDER.index(x[0]))

    dens = sorted({s["den"] for s in schools})
    rows = []
    for s in sorted(schools, key=lambda x: x["id"]):
        lat, lon, q, mun, city = geo.resolve(s)
        i = s["id"]
        p = pupils.get(i)
        addr = (s["street"] + " " + s["hn_raw"]).strip()
        rows.append([
            i, s["name"], addr, s["pc6"], city, mun, lat, lon, q, s["prov"], dens.index(s["den"]),
            p[0] if p else None, p[1] if p else None,
            mask.get(i, 0), exam.get(i), s["structuur"], s["web"] or None,
        ])
    out = {
        "v": 1,
        "years": {"pupils": "2025-2026 (peildatum 2025-10-01, provisional)", "exams": "2024-2025"},
        "cols": ["id", "name", "addr", "pc", "city", "mun", "lat", "lon", "g", "prov", "den",
                 "pupils", "pupils_lb", "tracks", "exam", "st", "web"],
        "bits": BIT,
        "prov": duo.PROVINCES,
        "den": dens,
        "rows": rows,
    }
    write_json_atomic(os.path.join(OUT, "schools_vo.json"), out)
    unmatched = len({k[0] for k in agg} - {s["id"] for s in schools})
    print("schools_vo.json rows:", len(rows), "| exam vestigingen not in address file:", unmatched)


if __name__ == "__main__":
    main()
