"""Step 7: build out/pc4.json  {"1011": [lat, lon, "Municipality"], ...} from the checkpointed raw files."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, OUT, read_jsonl, write_json_atomic


def main():
    geom = {r["pc4"]: r for r in read_jsonl(os.path.join(RAW, "pc4_geom.jsonl")) if "pc4" in r}
    muni = {r["pc4"]: r.get("m") for r in read_jsonl(os.path.join(RAW, "pc4_muni.jsonl"))}
    out = {}
    for p in sorted(geom):
        g = geom[p]
        out[p] = [round(g["lat"], 4), round(g["lon"], 4), muni.get(p) or ""]
    write_json_atomic(os.path.join(OUT, "pc4.json"), out)
    print("pc4.json entries:", len(out), "| without municipality:", sum(1 for v in out.values() if not v[2]))


if __name__ == "__main__":
    main()
