"""Step 18: build out/inspection.json from the Inspectie van het Onderwijs open data "oordelen" file.

Source: monthly ODS file (peildatum 1 November 2026), licence CC0 1.0 (stated in the page metadata, rightsHolder
Ministerie van OCW). Notes on the columns: Inspectie "Toelichting open data oordelen en standaarden 2025/2026".
The DUO copy (oordelen-v02) is a 2018 snapshot and is NOT used.

One ODS row = one object van toezicht (OVT): PO cluster (CLR), SO onderwijskundige eenheid (OKE), VO onderwijssoort (ODS),
sometimes a vestiging (VST). BetrokkenVestigingen lists the BRIN6 locations it covers; every location gets the row.

Per BRIN6 (po, sbo, so/vso and vo locations present in our schools files):
  o   overall judgement: Goed / Voldoende / Onvoldoende / (Zwak / Zeer zwak); VO: the worst of the rated opleidingen.
      "Basistoezicht" and "Geen eindoordeel" are NOT ratings: they are listed with o set to that text and only `b` filled
      (Basistoezicht: plus the metadata/standards when the row has them)
  d   latest Vaststellingsdatum of the rated rows (YYYY-MM-DD)
  x   VO: judgement per opleiding when more than one is rated
  st  standard-level judgements {ODS column: judgement string} of the school-level row (PO/SO CLR/OKE/VST row); for VO
      the standards shared by all rated opleidingen when they are identical
  xs  VO: {opleiding: {standard: judgement}} when the rated opleidingen differ
  t, tc, on, vd, pd, k, b   TypeOnderzoek, TypeOnderzoekCode, Onderzoeksnummer, Vaststellingsdatum, Publicatiedatum, Kader,
      [Bestuursnummer, Bestuursnaam] of the most recently determined rated row
"""
import datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, RAW, write_json_atomic
from xlsx import read_ods

FILE = "inspectie_oordelen_po_so_vo.ods"
AS_OF = "2026-11-01"
PAGE = "https://www.onderwijsinspectie.nl/documenten/2026/11/03/oordelen-1-november-2026"
NOTES_URL = ("https://www.onderwijsinspectie.nl/site/binaries/site-content/collections/documents/2025/09/02/"
             "toelichting-open-data-oordelen-en-standaarden-2025-2026/Toelichting_open_data_oordelen_en_standaarden_2025_2026.pdf")
RANK = {"Goed": 0, "Voldoende": 1, "Onvoldoende": 2, "Zwak": 3, "Zeer zwak": 4}   # higher = worse
STD_COLS = ["WV1", "WV2", "WV3", "WV4", "WV5", "WV6", "WV7", "1.1", "2.1", "2.2", "3.1", "4.1", "4.2", "5.1", "5.2", "6.1",
            "OP", "OP0", "OP1", "OP2", "OP2SN", "OP3", "OP4", "OP5", "OP6", "OP7", "OP8", "SK", "SK1", "SK2", "VS1", "VS2",
            "OR", "OR1", "OR2", "OR3", "SKA1", "SKA2", "SKA3", "KA", "KA1", "KA2", "KA3", "BA2"]

# Official names: Inspectie "Toelichting open data oordelen en standaarden 2025/2026", table "Standaarden" (kaders
# PO2021, PO2021_V23, SO2021, SO2021_V23, VO2021, VO2021_V23). verified = False when the code is only used by newer kader
# versions (V25/V26) or BTL/CN kaders that this note does not list; assumed unchanged.
LABELS = {
    "OP0": ("Basisvaardigheden", "Basic skills (language and arithmetic)"),
    "OP1": ("Aanbod", "Curriculum: what is taught"),
    "OP2": ("Zicht op ontwikkeling en begeleiding", "Monitoring pupils' development and guidance"),
    "OP3": ("Pedagogisch-didactisch handelen", "Teaching practice (pedagogical and didactic approach)"),
    "OP4": ("Onderwijstijd", "Instruction time"),
    "OP5": ("Praktijkvorming/Stage", "Practical training and work placements (SO, VO praktijkonderwijs)"),
    "OP6": ("Afsluiting", "Completion: final assessment and diploma"),
    "VS1": ("Veiligheid", "Safety"),
    "VS2": ("Schoolklimaat", "School climate"),
    "OR1": ("Resultaten", "Results"),
    "OR2": ("Sociale en maatschappelijke competenties", "Social and societal competences (PO and SO only)"),
    "SKA1": ("Visie, ambities en doelen", "Vision, ambitions and goals"),
    "SKA2": ("Uitvoering en kwaliteitscultuur", "Execution and quality culture"),
    "SKA3": ("Evaluatie, verantwoording en dialoog", "Evaluation, accountability and dialogue"),
}
# Codes of the 2017 framework (older reports). They do NOT occur in the current file; listed because the Inspectie site
# may still use them. In 2017 the codes OP4..OP8 and OR2 meant something else than in 2021.
LABELS_2017 = {
    "OP": "Onderwijsproces", "OP1": "Aanbod", "OP2": "Zicht op ontwikkeling (en begeleiding)", "OP3": "Didactisch handelen",
    "OP4": "(Extra) ondersteuning", "OP5": "Onderwijstijd (SO, VO)", "OP6": "Samenwerking", "OP7": "Praktijkvorming/stage (SO, VO)",
    "OP8": "Toetsing en afsluiting", "SK": "Schoolklimaat", "SK1": "Veiligheid", "SK2": "Pedagogisch klimaat",
    "OR": "Onderwijsresultaten", "OR1": "Resultaten", "OR2": "Sociale en maatschappelijke competenties", "OR3": "Vervolgsucces",
    "KA": "Kwaliteitszorg en ambitie", "KA1": "Kwaliteitszorg", "KA2": "Kwaliteitscultuur", "KA3": "Verantwoording en dialoog",
}
# Naleving wettelijke vereisten (WV): meaning depends on the kader, so keyed by kader
LABELS_WV = {
    "VO_WV2021": {"WV1": ("Vrijwillige ouderbijdrage (art. 2.92 lid 1 onder f WVO 2020)", "Voluntary parental contribution (legal requirement)"),
                  "WV2": ("Schoolplan (art. 24 WVO)", "School plan (legal requirement)")},
    "V0_WV2023": {"WV1": ("Vrijwillige ouderbijdrage (art. 2.92 lid 1 onder f WVO 2020)", "Voluntary parental contribution (legal requirement)")},
}
SCALE = {
    "Goed": "Good: meets the requirements and realises ambitions above them",
    "Voldoende": "Sufficient: meets the minimum requirements",
    "Onvoldoende": "Insufficient",
    "Zeer zwak": "Very weak (the lowest judgement)",
    "Zwak": "Weak (judgement of the earlier framework)",
    "Basistoezicht": "Basic supervision (earlier 'Goed' that expired); not a rating",
    "Geen eindoordeel": "No current final judgement (new or merged school, judgement older than four years, or not visited); not a rating",
    "Voldoet": "Meets the legal requirement (WV standards)",
    "Voldoet niet": "Does not meet the legal requirement (WV standards)",
    "Hersteld binnen onderzoek": "Restored during the inspection",
    "N.t.b.": "Meaning not documented in the Inspectie data notes",
    "Niet beoordeeld": "Not assessed",
    "Niet te beoordelen": "Not assessable",
}


def iso(d):
    d = (d or "").strip()
    return "%s-%s-%s" % (d[:4], d[4:6], d[6:8]) if len(d) == 8 and d.isdigit() else None


def main():
    ids = set()
    for n in ("schools_po.json", "schools_so.json", "schools_vo.json"):
        ids |= {r[0] for r in json.load(open(os.path.join(OUT, n), encoding="utf-8"))["rows"]}
    rows = next(iter(read_ods(os.path.join(RAW, FILE)).values()))
    hdr = rows[0]
    per = {}   # id -> list of row dicts
    for raw in rows[1:]:
        r = dict(zip(hdr, raw + [""] * (len(hdr) - len(raw))))
        if r["Sector"] not in ("PO", "SO", "VO") or r["Elementtype"] == "":
            continue
        for v in r["BetrokkenVestigingen"].split(","):
            i = v.strip().replace("|", "")
            if i in ids:
                per.setdefault(i, []).append(r)

    def std(r):
        return {c: r[c].strip() for c in STD_COLS if r.get(c, "").strip()}

    def meta(r):
        m = {}
        for key, col in (("t", "TypeOnderzoek"), ("tc", "TypeOnderzoekCode"), ("on", "Onderzoeksnummer"), ("k", "Kader")):
            if r[col].strip():
                m[key] = r[col].strip()
        for key, col in (("vd", "Vaststellingsdatum"), ("pd", "Publicatiedatum")):
            if iso(r[col]):
                m[key] = iso(r[col])
        return m

    schools, counts = {}, {"rated": 0, "geen_eindoordeel": 0, "basistoezicht": 0, "by_o": {}}
    for i, lst in sorted(per.items()):
        b = None
        for r in lst:
            if r["Bestuursnummer"].strip():
                b = [r["Bestuursnummer"].strip(), r["Bestuursnaam"].strip()]
                break
        q = lambda r: r["KwaliteitOnderwijs"].strip()
        rated = [r for r in lst if q(r) in RANK and iso(r["Vaststellingsdatum"])]
        if rated:
            worst = max(rated, key=lambda r: RANK[q(r)])
            rec = {"o": q(worst), "d": max(iso(r["Vaststellingsdatum"]) for r in rated)}
            latest = max(rated, key=lambda r: (iso(r["Vaststellingsdatum"]), RANK[q(r)]))
            ods = [r for r in rated if r["Elementtype"] == "ODS"]
            per_opl = {r["OVTNaam"].strip(): q(r) for r in ods}
            if len(per_opl) > 1:
                rec["x"] = dict(sorted(per_opl.items()))
            school_rows = [r for r in rated if r["Elementtype"] != "ODS"]
            if school_rows:
                s = std(max(school_rows, key=lambda r: iso(r["Vaststellingsdatum"])))
                if s:
                    rec["st"] = s
            else:
                by_opl = {r["OVTNaam"].strip(): std(r) for r in ods if std(r)}
                if by_opl:
                    vals = list(by_opl.values())
                    if all(v == vals[0] for v in vals) and len(by_opl) == len(ods):
                        rec["st"] = vals[0]
                    else:
                        rec["xs"] = dict(sorted(by_opl.items()))
            rec.update(meta(latest))
            counts["rated"] += 1
            counts["by_o"][rec["o"]] = counts["by_o"].get(rec["o"], 0) + 1
        else:
            bt = [r for r in lst if q(r) == "Basistoezicht"]
            rec = {"o": "Basistoezicht" if bt else "Geen eindoordeel"}
            if bt:
                r0 = max(bt, key=lambda r: iso(r["Vaststellingsdatum"]) or "")
                s = std(r0)
                if s:
                    rec["st"] = s
                rec.update(meta(r0))
                counts["basistoezicht"] += 1
            else:
                counts["geen_eindoordeel"] += 1
        if b:
            rec["b"] = b
        schools[i] = rec
    counts["listed"] = len(schools)
    used = sorted({c for s in schools.values() for c in list(s.get("st", {})) + [c for v in s.get("xs", {}).values() for c in v]})
    labels = {c: {"nl": LABELS[c][0], "en": LABELS[c][1]} for c in used if c in LABELS}
    out = {"v": 2, "as_of": AS_OF,
           "source": "Inspectie van het Onderwijs, open data oordelen po/so/vo, peildatum 1 november 2026",
           "source_url": PAGE, "notes_url": NOTES_URL,
           "licence": "CC0 1.0 Universal (rightsHolder: Ministerie van Onderwijs, Cultuur en Wetenschap)",
           "note": "Schools with o = Goed/Voldoende/Onvoldoende/Zwak/Zeer zwak are rated. o = 'Geen eindoordeel' or 'Basistoezicht' "
                   "means the Inspectie lists the school without a current final judgement: that is NOT a rating and not a bad sign. "
                   "The rated set skews towards schools the Inspectie visited because of earlier concerns. Do not rank or average these.",
           "deeplink": "https://toezichtresultaten.onderwijsinspectie.nl/extern?code={BRIN4}&sector={SECTOR}",
           "deeplink_note": "The Inspectie's own external-link route. BRIN4 = first four characters of the school id; SECTOR = PO for "
                            "schools_po (incl. sbo), SO for schools_so, VO for schools_vo. Opens the search results for that BRIN "
                            "(all its locations; a PO BRIN is usually one school). Tested for 00AR PO, 00AH VO and 06SV SO. "
                            "/zoek?q={BRIN4} also works; a BRIN6 query returns nothing. There is no per-school or per-report URL without "
                            "the site's API (not used: no stated licence).",
           "counts": counts,
           "scale": SCALE,
           "labels": labels,
           "labels_wv": {k: {c: {"nl": v[0], "en": v[1]} for c, v in d.items()} for k, d in LABELS_WV.items()},
           "labels_2017": LABELS_2017,
           "labels_note": "nl names are copied from the Inspectie data notes (url in notes_url), kaders PO2021, SO2021, VO2021 and their "
                          "_V23 revisions. The _V25/_V26 revisions and the BTL/CN kaders are not listed in those notes; their codes are "
                          "assumed to have the same meaning. Codes of the 2017 framework (labels_2017) do not occur in this file. "
                          "The meaning of a code is per kader (field k); WV codes depend on it (labels_wv).",
           "generated": datetime.date.today().isoformat(),
           "schools": schools}
    write_json_atomic(os.path.join(OUT, "inspection.json"), out)
    print("inspection.json schools:", len(schools), counts)


if __name__ == "__main__":
    main()
