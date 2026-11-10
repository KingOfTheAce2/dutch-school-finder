"""Step 1: download the DUO CSV files (skips files already present). Writes raw/MANIFEST.json."""
import os, sys, hashlib, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, http_get, write_json_atomic

B = "https://duo.nl/open_onderwijsdata/images/"
FILES = {
    "adressen_bo.csv": "02.-alle-schoolvestigingen-basisonderwijs.csv",
    "adressen_sbo_so_vso.csv": "09.-alle-vestigingen-sbo-so-en-vso.csv",
    "adressen_vo.csv": "02.-alle-vestigingen-vo.csv",
    "bo_leerlingen_2025-2026.csv": "03.-leerlingen-bo-sbo-leerjaar-geslacht-2025-2026.csv",
    "bo_advies_2024-2025.csv": "04-leerlingen-bo-sbo-schooladviezen-2024-2025.csv",
    "vo_leerlingen_2025.csv": "01.-leerlingen-vo-per-vestiging-naar-onderwijstype-2025.csv",
    "vo_examens_2024-2025.csv": "geslaagden-gezakten-en-cijfers-2024-2025.csv",
}

def main():
    man_path = os.path.join(RAW, "MANIFEST.json")
    man = json.load(open(man_path)) if os.path.exists(man_path) else {}
    for local, remote in FILES.items():
        p = os.path.join(RAW, local)
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            data = http_get(B + remote, timeout=120)
            if data[:15].lstrip().lower().startswith(b"<!doctype") or data[:6].lower() == b"<html>":
                raise SystemExit("got HTML instead of CSV for " + remote)
            with open(p, "wb") as f:
                f.write(data)
            time.sleep(1)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        man[local] = {"url": B + remote, "bytes": os.path.getsize(p), "sha256": h}
        print("ok", local, os.path.getsize(p))
    write_json_atomic(man_path, man)

if __name__ == "__main__":
    main()
