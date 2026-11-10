"""Step 18: build out/inspection.json from the Inspectie van het Onderwijs open data "oordelen" file.

Source: monthly ODS file (peildatum 1 November 2026), licence CC0 1.0 (stated in the page metadata, rightsHolder
Ministerie van OCW). The DUO copy (oordelen-v02) is a 2018 snapshot and is NOT used.

Per BRIN6 (po, sbo and vo schools present in our schools files):
  o  overall judgement of the school: the single judgement for PO; for VO the lowest judgement among the rated opleidingen
  d  date the judgement was set (Vaststellingsdatum), latest of the rated rows
  x  VO only: judgement per opleiding when more than one is rated
Rows with "Geen eindoordeel" / "Basistoezicht" carry no judgement and are left out. SO/VSO are not in our files.
"""
import datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, RAW, write_json_atomic
from xlsx import read_ods

FILE = "inspectie_oordelen_po_so_vo.ods"
AS_OF = "2026-11-01"
PAGE = "https://www.onderwijsinspectie.nl/documenten/2026/11/03/oordelen-1-november-2026"
RANK = {"Goed": 0, "Voldoende": 1, "Onvoldoende": 2, "Zwak": 3, "Zeer zwak": 4}   # higher = worse


def iso(d):
    d = (d or "").strip()
    return "%s-%s-%s" % (d[:4], d[4:6], d[6:8]) if len(d) == 8 and d.isdigit() else None


def main():
    ids = set()
    for n in ("schools_po.json", "schools_vo.json"):
        ids |= {r[0] for r in json.load(open(os.path.join(OUT, n), encoding="utf-8"))["rows"]}
    sheets = read_ods(os.path.join(RAW, FILE))
    rows = next(iter(sheets.values()))
    hdr = rows[0]
    acc = {}   # id -> list of (rating, date, opleiding or None)
    for raw in rows[1:]:
        r = dict(zip(hdr, raw + [""] * (len(hdr) - len(raw))))
        q = r["KwaliteitOnderwijs"].strip()
        if q not in RANK or r["Sector"] not in ("PO", "VO"):
            continue
        d = iso(r["Vaststellingsdatum"])
        if not d:
            continue
        opl = r["OVTNaam"].strip() if r["Elementtype"] == "ODS" else None
        for v in r["BetrokkenVestigingen"].split(","):
            i = v.strip().replace("|", "")
            if i in ids:
                acc.setdefault(i, []).append((q, d, opl))
    schools = {}
    for i, lst in sorted(acc.items()):
        worst = max(lst, key=lambda t: RANK[t[0]])[0]
        rec = {"o": worst, "d": max(t[1] for t in lst)}
        per = {t[2]: t[0] for t in lst if t[2]}
        if len(per) > 1:
            rec["x"] = dict(sorted(per.items()))
        schools[i] = rec
    out = {"v": 1, "as_of": AS_OF,
           "source": "Inspectie van het Onderwijs, open data oordelen po/vo, peildatum 1 november 2026",
           "source_url": PAGE,
           "licence": "CC0 1.0 Universal (rightsHolder: Ministerie van Onderwijs, Cultuur en Wetenschap)",
           "note": "Only schools with a published eindoordeel are listed. Most schools have no current eindoordeel "
                   "(Geen eindoordeel), so a missing school is NOT a rating, and the listed schools skew towards ones "
                   "the Inspectie visited because of earlier concerns. Do not rank or average these.",
           "generated": datetime.date.today().isoformat(),
           "schools": schools}
    write_json_atomic(os.path.join(OUT, "inspection.json"), out)
    c = {}
    for s in schools.values():
        c[s["o"]] = c.get(s["o"], 0) + 1
    print("inspection.json schools:", len(schools), c)


if __name__ == "__main__":
    main()
