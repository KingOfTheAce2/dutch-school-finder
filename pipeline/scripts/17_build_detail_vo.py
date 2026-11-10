"""Step 17: build out/detail_vo.json (per-school detail for secondary schools).

Fields per BRIN6 (all optional):
  pt   total pupils per peildatum year [year, n, lb]  (exact cells summed; lb=1 = lower bound because DUO suppressed a cell)
  tp   pupils by track, latest year (null = only suppressed cells); tpl lists tracks whose number is a lower bound
  pr   pass rate per track and exam year [year, candidates, pass %]; a trailing 1 = computed from the unsuppressed
       rows only (some sector/afdeling rows of that track were suppressed)
  ce   mean central-exam grade per track and exam year [year, mean, candidates (, 1)] from the DUO "geslaagden,
       gezakten en cijfers" files: candidate-weighted mean of the sector/afdeling row means, over rows with >= 5
       exact candidates and a published CE mean; a trailing 1 = some rows of that track were suppressed
  zb   [pupils, afstromers, zittenblijvers, opstromers] school year 2024/25 vs 2025/26 (null = suppressed)
  ov   Inspectie onderwijsresultaten 2026 per onderwijssoort {track: [ob, bb, ce, verdict]}; ob = onderbouwsnelheid %,
       bb = bovenbouwsucces %, ce = mean central-exam grade, each [3-year value, norm after correction, 1 above norm | 0 below];
       verdict = the Inspectie's calculated verdict ("voldoende", "onvoldoende", "onvoldoende, tenzij"), null = no verdict
  op   Inspectie onderwijspositie t.o.v. advies po (per vestiging) [value, norm, 1 above norm | 0 below]
  cm   top 10 home PC4s [pc4, pupils] (trailing 1 = lower bound), cmo = % of known pupils living outside the top 10
Suppression: "<5" => null. The SLAAGPERC column of the DUO file is never used (it can reveal a suppressed GESLAAGDEN
cell); pass % is geslaagden / kandidaten from exact cells only, shown only when the known candidates are >= 5.
"""
import datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, RAW, write_json_atomic
import duo
from xlsx import read_ods

PUPIL_YEARS = [2021, 2022, 2023, 2024, 2025]
EXAM_FILE = "vo_examenkandidaten_2020-2025.csv"
CE_FILES = {2021: "vo_examens_2020-2021.csv", 2022: "vo_examens_2021-2022.csv", 2023: "vo_examens_2022-2023.csv",
            2024: "vo_examens_2023-2024.csv", 2025: "vo_examens_2024-2025.csv"}   # exam year -> file
ZB_FILE, ZB_YEARS = "vo_zittenblijvers_vestiging_2024-2025_2025-2026.csv", "2024-2025 to 2025-2026"
OV_FILE = "inspectie_onderwijsresultaten_vo_2026.ods"
OV_TRACK = {"vmbo b": "VMBO-B", "vmbo k": "VMBO-K", "vmbo (g)t": "VMBO-GL/TL", "havo": "HAVO", "vwo": "VWO"}
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

    # mean central-exam grade (CE) per track and year. Rows with fewer than 5 exact candidates (or a CE mean that is
    # not published) are left out; the row means are weighted by candidate count.
    ce = {}   # (id, track, year) -> [sum(n*grade), n, suppressed rows]
    for y, fn in CE_FILES.items():
        for r in duo.read_csv_auto(fn):
            t = r["ONDERWIJSTYPE VO"].strip()
            if t in ("HAVO", "VWO"):
                lab = t
            elif t == "VMBO":
                lab = {"BL": "VMBO-B", "KL": "VMBO-K", "GL": "VMBO-GL/TL", "TL": "VMBO-GL/TL"}.get(r["LEERWEG VMBO"].strip())
            else:
                lab = None
            i = (r.get("VESTIGINGSCODE") or r.get("VESTIGINGSNUMMER") or "").strip()
            if not lab or i not in det:
                continue
            n = cell(r["EXAMENKANDIDATEN"])
            try:
                g = float(r["GEMIDDELD CIJFER CENTRAAL EXAMEN"].replace(",", "."))
            except ValueError:
                g = None
            x = ce.setdefault((i, lab, y), [0.0, 0, 0])
            if n is None or g is None or not 1.0 <= g <= 10.0:
                if num(r["EXAMENKANDIDATEN"]) != 0:
                    x[2] += 1
            else:
                x[0] += n * g
                x[1] += n
    cem = {}
    for (i, lab, y), (sg, n, sp) in ce.items():
        if n >= 5:
            cem.setdefault(i, {}).setdefault(lab, []).append([y, round(sg / n, 2), n] + ([1] if sp else []))
    for i, d in cem.items():
        det[i]["ce"] = {lab: sorted(d[lab]) for lab in TRACKS if lab in d}

    # repeaters and up/down-streaming (school year 2024/25 -> 2025/26); cells "<5" => null
    for r in duo.read_csv_auto(ZB_FILE):
        i = brin6(r)
        if i in det:
            z = [num(r["AANTAL_LEERLINGEN"]), num(r["AANTAL_AFSTROMERS"]), num(r["AANTAL_ZITTENBLIJVERS"]), num(r["AANTAL_OPSTROMERS"])]
            if z[0] is not None and z[0] >= 5:
                det[i]["zb"] = z

    # Inspectie onderwijsresultaten VO (CC0): indicators per vestiging and onderwijssoort, 3-year averages. Values the
    # Inspectie did not compute (too few pupils) are empty in the file and stay null here.
    def fl(v):
        try:
            return float(v.replace(",", "."))
        except ValueError:
            return None

    ov_rows = next(iter(read_ods(os.path.join(RAW, OV_FILE)).values()))
    oh = ov_rows[0]
    for raw in ov_rows[1:]:
        r = dict(zip(oh, raw + [""] * (len(oh) - len(raw))))
        i = r["brin"].strip() + r["vestnr"].strip().zfill(2)
        lab = OV_TRACK.get(r["onderwijssoort"].strip())
        if i not in det:
            continue

        def ind(val, norm, oordeel):
            v, n_ = fl(r[val]), fl(r[norm])
            o = r[oordeel].strip()
            if v is None or n_ is None or o not in ("boven de norm", "onder de norm"):
                return None
            return [v, n_, 1 if o == "boven de norm" else 0]
        op = ind("obopaf_gem_2324_2425_2526", "obopaf_norm", "obopaf_oordeel_2324_2425_2526")
        if op:
            det[i]["op"] = op
        if not lab:
            continue
        ob = ind("obdoor_gem_2223_2324_2425", "obdoor_norm_na_cor", "obdoor_oordeel_2223_2324_2425")
        bb = ind("bbdoor_gem_2223_2324_2425", "bbdoor_norm_na_cor", "bbdoor_oordeel_2223_2324_2425")
        ce_ = ind("ce_gem_2223_2324_2425", "ce_norm_na_cor", "ce_oordeel_2223_2324_2425")
        vd_ = r["berekend_oordeel"].strip()
        vd_ = None if vd_ in ("", "geen oordeel") else vd_
        if ob or bb or ce_ or vd_:
            det[i].setdefault("ov", {})[lab] = [ob, bb, ce_, vd_]
    for d in det.values():
        if "ov" in d:
            d["ov"] = {lab: d["ov"][lab] for lab in TRACKS if lab in d["ov"]}

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
           "years": {"pupils": PUPIL_YEARS, "exams": exam_years, "ce": sorted(CE_FILES), "ov": "Inspectie onderwijsresultaten VO 2026: 2022/23 to 2024/25 (op: 2023/24 to 2025/26)", "zb": ZB_YEARS, "catchment": CATCH_YEAR},
           "schools": schools}
    write_json_atomic(os.path.join(OUT, "detail_vo.json"), out)
    print("detail_vo.json schools:", len(schools), "of", len(ids), "| exam years", exam_years)


if __name__ == "__main__":
    main()
