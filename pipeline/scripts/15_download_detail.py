"""Step 15: download the extra DUO files used by the detail_po / detail_vo builds (skips files already present).

Adds entries to raw/MANIFEST.json (URL, size, sha256). Polite: one request per ~1.5 s. Files that DUO publishes only
as .xlsx (doorstroomtoets scores, some advice years) are stored as .xlsx and read with the stdlib in xlsx.py.
A 404 / redirect-to-HTML for an optional file is logged and skipped (the build then simply has fewer years).
"""
import hashlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, http_get, write_json_atomic

B = "https://duo.nl/open_onderwijsdata/images/"
FILES = {}
# PO pupils per vestiging (peildatum 1 Oct of the first year of the school year); 2025-2026 is already step 1
for y in (2021, 2022, 2023, 2024):
    FILES["bo_leerlingen_%d-%d.csv" % (y, y + 1)] = "03.-leerlingen-bo-sbo-leerjaar-geslacht-%d-%d.csv" % (y, y + 1)
# VO pupils per vestiging naar onderwijstype (2025 is step 1)
for y in (2021, 2022, 2023, 2024):
    FILES["vo_leerlingen_%d.csv" % y] = "01.-leerlingen-vo-per-vestiging-naar-onderwijstype-%d.csv" % y
# PO schooladviezen history: csv where DUO has one, xlsx otherwise
FILES["bo_advies_2021-2022.csv"] = "04-leerlingen-bo-sbo-schooladviezen-2021-2022.csv"
FILES["bo_advies_2022-2023.csv"] = "04-leerlingen-bo-sbo-schooladviezen-2022-2023.csv"
FILES["bo_advies_2023-2024.xlsx"] = "04.-leerlingen-bo-sbo-schooladviezen-2023-2024.xlsx"
FILES["bo_advies_2025-2026.xlsx"] = "04.-leerlingen-bo-sbo-schooladviezen-2025-2026.xlsx"
# doorstroomtoets averages (xlsx only)
FILES["bo_eindscores_2024-2025.xlsx"] = "5.-gemiddelde-scores-doorstroomtoets-bo-sbo-2024-2025.xlsx"
FILES["bo_eindscores_2025-2026.xlsx"] = "5.-gemiddelde-scores-doorstroomtoets-bo-sbo-2025-2026.xlsx"
# Inspectie van het Onderwijs open data oordelen (ODS, licence CC0 1.0 per the page metadata); monthly file, bump when re-running
FILES["inspectie_oordelen_po_so_vo.ods"] = ("https://www.onderwijsinspectie.nl/site/binaries/site-content/collections/documents/"
                                           "2026/11/03/oordelen-1-november-2026/20261102-oordeel-en-standaard-po-so-vo.ods")
# average / median home-to-school distance
FILES["bo_afstand_2025-2026.csv"] = "05.-gemiddelde-afstand-tussen-woonadres-leerling-en-schoolvestiging-2025-2026.csv"
# VO: multi-year exam candidates and pass rates; pupil home postcode (catchment)
FILES["vo_examenkandidaten_2020-2025.csv"] = "examenkandidaten-en-geslaagden-2020-2025.csv"
FILES["vo_postcode_2025.csv"] = "02.-leerlingen-per-vestiging-naar-postcode-en-leerjaar-2025.csv"


def looks_bad(data, name):
    head = data[:600].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        return True
    if name.endswith((".xlsx", ".ods")) and data[:2] != b"PK":
        return True
    return False


def main():
    man_path = os.path.join(RAW, "MANIFEST.json")
    man = json.load(open(man_path, encoding="utf-8")) if os.path.exists(man_path) else {}
    for local, remote in FILES.items():
        p = os.path.join(RAW, local)
        url = remote if remote.startswith("http") else B + remote
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            try:
                data = http_get(url, timeout=180)
            except Exception as e:                      # noqa: BLE001 - optional file, report and go on
                print("SKIP (download failed)", local, e)
                continue
            if looks_bad(data, local):
                print("SKIP (not a data file)", local)
                continue
            tmp = p + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, p)
            time.sleep(1.5)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        man[local] = {"url": url, "bytes": os.path.getsize(p), "sha256": h}
        write_json_atomic(man_path, man)                 # checkpoint after each file
        print("ok", local, os.path.getsize(p))


if __name__ == "__main__":
    main()
