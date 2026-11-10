"""Step 16: build out/detail_po.json (per-school detail for primary schools).

Fields per BRIN6 (all optional):
  pt  pupils per peildatum year (sum of the exact LEERJAAR cells; lb=1 when DUO suppressed a cell, so the sum is a lower bound)
  es  doorstroomtoets averages per test (latest year; only tests with >= 5 pupils)
  dm  [mean m, median m, n pupils] home-to-school distance
  lj  pupils per leerjaar 1-8, latest year: [8 values, null = suppressed cell] (cells are never recovered by subtraction)
  rn  referentieniveaus (doorstroomtoets, latest year): {"lezen":[%1F,%2F,n],"taal":[%1F,%2F,n],"rekenen":[%1F,%1S,n]}
  hv  heroverwegingen (latest year): [n_reconsidered, n_raised, n_leavers]
  at  advice mix per year, same encoding as `adv` in schools_po: [year, n, suppressed cells, [12 shares]]
Suppression: "<5" / -1 / NA => null. Cells holding 1 to 4 in the older DUO files (published unsuppressed) are treated as
suppressed in the advice mix so every year follows the current DUO rule. DUO totals (TOTAAL columns) are never used, so
a suppressed cell can not be recovered by subtraction.
"""
import datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, RAW, write_json_atomic
import duo
from xlsx import read_xlsx_dicts

PUPIL_YEARS = [2021, 2022, 2023, 2024, 2025]
PUPIL_FILE = "bo_leerlingen_%d-%d.csv"
ADV_FILES = {  # peildatum year -> file
    2021: "bo_advies_2021-2022.csv", 2022: "bo_advies_2022-2023.csv", 2023: "bo_advies_2023-2024.xlsx",
    2024: "bo_advies_2024-2025.csv", 2025: "bo_advies_2025-2026.xlsx",
}
ES_FILE, ES_YEAR = "bo_eindscores_2025-2026.xlsx", "2025-2026"
DIST_FILE, DIST_YEAR = "bo_afstand_2025-2026.csv", "2025-2026"
LEVELS = ["VSO", "PRO", "VMBO_B", "VMBO_B_K", "VMBO_K", "VMBO_K_GT", "VMBO_GT", "VMBO_GT_HAVO",
          "HAVO", "HAVO_VWO", "VWO", "ADVIES_NIET_MOGELIJK"]
RN_FILE, RN_YEAR = "bo_referentieniveaus_2025-2026.xlsx", "2025-2026"
HV_FILE, HV_YEAR = "bo_heroverwegingen_2025-2026.xlsx", "2025-2026"
TEST_NAMES = {"ROUTE 8": "Route 8"}


def num(v):
    v = (v or "").strip()
    return int(v) if re.fullmatch(r"\d+", v) else None


def adv_cell(v):
    """Exact value or None. 1..4 is treated as suppressed (DUO rule; older files published them), 0 stays 0."""
    n = num(v)
    if n is None or 1 <= n <= 4:
        return None
    return n


def advice_year(fname):
    if fname.endswith(".xlsx"):
        rows = read_xlsx_dicts(os.path.join(RAW, fname))
        key = lambda r: r["VESTIGINGSCODE"].strip()
    else:
        rows = duo.read_csv_auto(fname)
        key = lambda r: r["INSTELLINGSCODE"].strip() + r["VESTIGINGSCODE"].strip()
    out = {}
    for r in rows:
        have = [l in r for l in LEVELS]
        vals = [adv_cell(r[l]) if l in r else None for l in LEVELS]
        n = sum(v for v in vals if v is not None)
        s = sum(1 for l, v in zip(LEVELS, vals) if l in r and v is None)
        if n == 0 and s == 0:
            continue
        shares = None
        if n > 0:
            shares = [None if v is None else round(100.0 * v / n, 1) for v in vals]
        out[key(r)] = [n, s, shares]
    return out


def main():
    po = json.load(open(os.path.join(OUT, "schools_po.json"), encoding="utf-8"))
    ids = {r[0] for r in po["rows"]}
    det = {i: {} for i in ids}

    # pupils per year
    for y in PUPIL_YEARS:
        fn = PUPIL_FILE % (y, y + 1)
        tot = {}
        for r in duo.read_csv_auto(fn):
            i = r["INSTELLINGSCODE"].strip() + r["VESTIGINGSCODE"].strip()
            p = tot.setdefault(i, [0, 0, 0])
            for k in range(1, 9):
                v = adv_cell(r["LEERJAAR_%d" % k])
                if v is None:
                    p[1] = 1
                else:
                    p[0] += v
                    p[2] = 1
        for i, (s, lb, any_exact) in tot.items():
            if i in det:
                n = s if (any_exact or not lb) else None
                det[i].setdefault("pt", []).append([y, n, lb])

    # pupils per leerjaar, latest year (suppressed cell => null; no subtraction from totals)
    for r in duo.read_csv_auto(PUPIL_FILE % (PUPIL_YEARS[-1], PUPIL_YEARS[-1] + 1)):
        i = r["INSTELLINGSCODE"].strip() + r["VESTIGINGSCODE"].strip()
        if i in det:
            lj = [adv_cell(r["LEERJAAR_%d" % k]) for k in range(1, 9)]
            if any(v is not None for v in lj):
                det[i]["lj"] = lj

    # referentieniveaus. DUO gives mutually exclusive counts per level (lager dan 1F / 1F / 2F, rekenen 1F / 1S);
    # the output is the share of tested pupils who reached AT LEAST the level. TOTAAL "<5" => school omitted.
    for r in read_xlsx_dicts(os.path.join(RAW, RN_FILE)):
        i = r["VESTIGINGSCODE"].strip()
        n = num(r["TOTAAL_REFERENTIENIVEAUS"])
        if i not in det or n is None or n < 5:
            continue
        out = {}
        for key, low, mid, top, atleast in (("lezen", "LV_LAGER1F", "LV_1F", "LV_2F", ("12", "2")),
                                            ("taal", "TV_LAGER1F", "TV_1F", "TV_2F", ("12", "2")),
                                            ("rekenen", "REKENEN_LAGER1F", "REKENEN_1F", "REKENEN_1S", ("12", "2"))):
            a, b, c = num(r[low]), num(r[mid]), num(r[top])
            p1 = None if b is None or c is None else round(100.0 * (b + c) / n, 1)   # reached 1F (or higher)
            p2 = None if c is None else round(100.0 * c / n, 1)                       # reached 2F (lezen/taal) or 1S (rekenen)
            if p1 is not None and a is not None and a + b + c != n:
                p1 = p2 = None                                                          # inconsistent row: do not publish
            if p1 is not None or p2 is not None:
                out[key] = [p1, p2, n]
        if out:
            det[i]["rn"] = out

    # heroverwegingen en bijgestelde adviezen (cells "<5" => null; the file's own TOTAAL "<5" => school omitted)
    for r in read_xlsx_dicts(os.path.join(RAW, HV_FILE)):
        i = r["VESTIGINGSCODE"].strip()
        n = num(r["TOTAAL"])
        if i not in det or n is None or n < 5:
            continue
        h, b = num(r["HEROVERWEGING_TOTAAL"]), num(r["BIJSTELLING"])
        if h is not None or b is not None:
            det[i]["hv"] = [h, b, n]

    # doorstroomtoets averages
    es_rows = read_xlsx_dicts(os.path.join(RAW, ES_FILE))
    tests = sorted({k[:-7] for k in es_rows[0] if k.endswith("_AANTAL")})
    for r in es_rows:
        i = r["VESTIGINGSCODE"].strip()
        if i not in det:
            continue
        out = []
        for t in tests:
            n = num(r[t + "_AANTAL"])
            try:
                avg = float(r[t + "_GEM"].replace(",", "."))
            except ValueError:
                avg = None
            if n is None or n < 5 or avg is None:
                continue
            out.append([TEST_NAMES.get(t, t), round(avg, 1), n])
        if out:
            det[i]["es"] = out

    # distance
    for r in duo.read_csv_auto(DIST_FILE):
        i = r["INSTELLINGSCODE"].strip() + r["VESTIGINGSCODE"].strip()
        n, mean, med = num(r["LEERLINGEN"]), num(r["GEMIDDELDE_AFSTAND"]), num(r["MEDIAAN_AFSTAND"])
        if i in det and n is not None and n >= 5 and mean is not None:
            if med is None or (med == 0 and mean >= 500):
                med = None   # DUO median 0 beside a large mean (43 % of schools) is implausible; keep only the mean
            det[i]["dm"] = [mean, med, n]

    # advice history
    for y in sorted(ADV_FILES):
        for i, (n, s, sh) in advice_year(ADV_FILES[y]).items():
            if i in det:
                det[i].setdefault("at", []).append([y, n, s, sh])

    schools = {i: d for i, d in sorted(det.items()) if d}
    out = {"v": 1, "generated": datetime.date.today().isoformat(),
           "years": {"pupils": PUPIL_YEARS, "eindscore": ES_YEAR, "refniveau": RN_YEAR, "heroverweging": HV_YEAR, "dist": DIST_YEAR, "advice": sorted(ADV_FILES)},
           "schools": schools}
    write_json_atomic(os.path.join(OUT, "detail_po.json"), out)
    print("detail_po.json schools:", len(schools), "of", len(ids))


if __name__ == "__main__":
    main()
