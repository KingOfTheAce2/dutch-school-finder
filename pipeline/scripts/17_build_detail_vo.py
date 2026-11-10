"""Step 17: build out/detail_vo.json (per-school detail for secondary schools).

Fields per BRIN6 (all optional):
  pt   total pupils per peildatum year [year, n, lb]  (exact cells summed; lb=1 = lower bound because DUO suppressed a cell)
  tp   pupils by track, latest year (null = only suppressed cells); tpl lists tracks whose number is a lower bound
  pr   pass rate per track and exam year [year, candidates, pass %]; a trailing 1 = computed from the unsuppressed
       rows only (some sector/afdeling rows of that track were suppressed)
  cm   top 10 home PC4s [pc4, pupils] (trailing 1 = lower bound), cmo = % of known pupils living outside the top 10
Suppression: "<5" => null. The SLAAGPERC column of the DUO file is never used (it can reveal a suppressed GESLAAGDEN
cell); pass % is geslaagden / kandidaten from exact cells only, shown only when the known candidates are >= 5.
"""
import datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, write_json_atomic
import duo

PUPIL_YEARS = [2021, 2022, 2023, 2024, 2025]
EXAM_FILE = "vo_examenkandidaten_2020-2025.csv"
POSTCODE_FILE = "vo_postcode_2025.csv"
CATCH_YEAR = 2025
TRACKS = ["VMBO-B", "VMBO-K", "VMBO-GL/TL", "HAVO", "VWO", "PRO", "BRUGJAAR"]

# DUO "ONDERWIJSTYPE VO EN LEER- OF VERBLIJFSJAAR" -> output track label (anything else, e.g. Engelse Stroom,
# International Baccalaureate, European School, VAVO, is counted in `pt` but has no track entry)
PUPIL_TRACK = {
    "VMBO BL lj 3-4": "VMBO-B", "VMBO KL lj 3-4": "VMBO-K",
    "VMBO GL lj 3-4": "VMBO-GL/TL", "VMBO TL lj 3-4": "VMBO-GL/TL",
    "HAVO lj 4-5": "HAVO", "VWO lj 4-6": "VWO", "Praktijkonderwijs alle vj": "PRO",
    "Brugjaar 1-2": "BRUGJAAR", "HAVO/VWO lj 3": "BRUGJAAR",
}
# exam file: ONDERWIJSTYPE VO + first words of OPLEIDINGSNAAM ("VMBO B - zorg en welzijn"); "VMBO LWT" is left out
EXAM_VMBO = {"VMBO B": "VMBO-B", "VMBO K": "VMBO-K", "VMBO G": "VMBO-GL/TL", "VMBO T": "VMBO-GL/TL"}


def num(v):
    v = (v or "").strip()
    return int(v) if re.fullmatch(r"\d+", v) else None


def cell(v):
    """Pupil cell: exact value, or None when suppressed. DUO's older files (2021 and earlier years) publish 1..4
    unsuppressed; the current rule hides them, so they are treated as suppressed to keep all years comparable."""
    n = num(v)
    return None if n is None or 1 <= n <= 4 else n


def brin6(r):
    b = (r.get("INSTELLINGSCODE") or r.get("BRIN NUMMER") or r.get("INSTELLING") or "").strip()
    v = (r.get("VESTIGINGSCODE") or r.get("VESTIGINGSNUMMER") or "").strip()
    return b + v.zfill(2) if len(v) <= 2 else v


def main():
    vo = json.load(open(os.path.join(OUT, "schools_vo.json"), encoding="utf-8"))
    ids = {r[0] for r in vo["rows"]}
    det = {i: {} for i in ids}

    # pupils per year and by track
    for y in PUPIL_YEARS:
        tot, trk = {}, {}
        for r in duo.read_csv_auto("vo_leerlingen_%d.csv" % y):
            t = r["ONDERWIJSTYPE VO EN LEER- OF VERBLIJFSJAAR"].strip()
            if t.endswith("uitbest. aan VAVO"):
                continue
            i = brin6(r)
            cells = [cell(v) for k, v in r.items() if k.startswith("LEER- OF VERBLIJFSJAAR")]
            s = sum(c for c in cells if c is not None)
            lb = int(any(c is None for c in cells))
            ex = int(any(c is not None for c in cells))
            a = tot.setdefault(i, [0, 0, 0])
            a[0] += s
            a[1] |= lb
            a[2] |= ex
            lab = PUPIL_TRACK.get(t)
            if lab:
                b = trk.setdefault(i, {}).setdefault(lab, [0, 0, 0])
                b[0] += s
                b[1] |= lb
                b[2] |= ex
        for i, (s, lb, ex) in tot.items():
            if i in det:
                det[i].setdefault("pt", []).append([y, s if (ex or not lb) else None, lb])
        if y == PUPIL_YEARS[-1]:
            for i, d in trk.items():
                if i not in det:
                    continue
                tp, tpl = {}, []
                for lab in TRACKS:
                    if lab not in d:
                        continue
                    s, lb, ex = d[lab]
                    if s == 0 and not lb:
                        continue                      # track row exists with zero pupils
                    tp[lab] = s if ex else None
                    if lb and ex:
                        tpl.append(lab)
                if tp:
                    det[i]["tp"] = tp
                    if tpl:
                        det[i]["tpl"] = tpl

    # exam pass rates
    rows = duo.read_csv_auto(EXAM_FILE)
    ycols = sorted({re.search(r"SCHOOLJAAR (\d{4})-(\d{4}) - TOTAAL", k).groups() for k in rows[0]
                    if k.startswith("EXAMENKANDIDATEN SCHOOLJAAR") and k.endswith("TOTAAL")})
    exam_years = [int(b) for a, b in ycols]
    agg = {}   # (id, track, year) -> [cand, passed, suppressed rows]
    for r in rows:
        t = r["ONDERWIJSTYPE VO"].strip()
        if t in ("HAVO", "VWO"):
            lab = t
        elif t == "VMBO":
            on = r["OPLEIDINGSNAAM"].strip()
            m = re.match(r"(VMBO [A-Z]+)\b", on)
            lab = EXAM_VMBO.get(m.group(1)) if m else None
        else:
            lab = None
        if not lab:
            continue
        i = r["VESTIGINGSCODE"].strip()
        for a, b in ycols:
            rc = r["EXAMENKANDIDATEN SCHOOLJAAR %s-%s - TOTAAL" % (a, b)].strip()
            if rc == "":
                continue
            c = num(rc)
            g = num(r["GESLAAGDEN SCHOOLJAAR %s-%s - TOTAAL" % (a, b)])
            x = agg.setdefault((i, lab, int(b)), [0, 0, 0])
            if c is None or g is None:
                x[2] += 1
            else:
                x[0] += c
                x[1] += g
    pr = {}
    for (i, lab, y), (c, g, sp) in agg.items():
        if i not in det:
            continue
        if c >= 5:
            rec = [y, c, round(100.0 * g / c, 1)] + ([1] if sp else [])
        elif c == 0 and sp == 0:
            continue                                   # rows with zero candidates
        else:
            rec = [y, None, None]                      # fewer than 5 known candidates, or all suppressed
        pr.setdefault(i, {}).setdefault(lab, []).append(rec)
    for i, d in pr.items():
        det[i]["pr"] = {lab: sorted(d[lab]) for lab in TRACKS if lab in d}

    # catchment: pupil home PC4 (latest year)
    pc, known = {}, {}
    for r in duo.read_csv_auto(POSTCODE_FILE):
        i = brin6(r)
        if i not in det:
            continue
        cells = [cell(r["LEER- OF VERBLIJFSJAAR %d" % k]) for k in range(1, 7)]
        s = sum(c for c in cells if c is not None)
        lb = int(any(c is None for c in cells))
        known[i] = known.get(i, 0) + s
        p = r["POSTCODE LEERLING"].strip()
        if re.fullmatch(r"[1-9][0-9]{3}", p):
            a = pc.setdefault(i, {}).setdefault(p, [0, 0])
            a[0] += s
            a[1] |= lb
    for i, d in pc.items():
        top = sorted(((v[0], p, v[1]) for p, v in d.items() if v[0] >= 5), key=lambda x: (-x[0], x[1]))[:10]
        if not top:
            continue
        det[i]["cm"] = [[p, n] + ([1] if lb else []) for n, p, lb in top]
        k = known.get(i, 0)
        det[i]["cmo"] = round(100.0 * (k - sum(n for n, _, _ in top)) / k, 1) if k > 0 else None

    schools = {i: d for i, d in sorted(det.items()) if d}
    out = {"v": 1, "generated": datetime.date.today().isoformat(),
           "years": {"pupils": PUPIL_YEARS, "exams": exam_years, "catchment": CATCH_YEAR},
           "schools": schools}
    write_json_atomic(os.path.join(OUT, "detail_vo.json"), out)
    print("detail_vo.json schools:", len(schools), "of", len(ids), "| exam years", exam_years)


if __name__ == "__main__":
    main()
