"""Resolve school coordinates from the geocode cache with the documented fallback chain.

quality code (field "g" in the output):
  0 = exact address match in BAG via PDOK Locatieserver
  1 = fallback: PC6 (postcode) centroid from Locatieserver
  2 = fallback: PC4 centroid (CBS postcode4 geometry)
  3 = no coordinates
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, read_jsonl
import duo


class Geo:
    def __init__(self):
        self.cache = {r["k"]: r for r in read_jsonl(os.path.join(RAW, "geocode_cache.jsonl")) if "k" in r}
        self.pc4 = {r["pc4"]: r for r in read_jsonl(os.path.join(RAW, "pc4_geom.jsonl")) if "pc4" in r}
        self.pc4m = {r["pc4"]: r.get("m") for r in read_jsonl(os.path.join(RAW, "pc4_muni.jsonl"))}
        self.gemnames = {}

    def learn_gemeente_names(self, rows_lists):
        """gemeentenummer -> properly cased name, taken from the DUO files that use mixed case."""
        for rows in rows_lists:
            for r in rows:
                n, m = r.get("GEMEENTENUMMER", "").strip(), r.get("GEMEENTENAAM", "").strip()
                if n and m and m != m.upper():
                    self.gemnames.setdefault(n, m)

    def resolve(self, s):
        """Return (lat, lon, quality, municipality, city)."""
        k = duo.geo_key(s)
        c = self.cache.get(k) if k else None
        pc6 = s["pc6"]
        pc4 = pc6[:4]
        if c and c.get("s") == "ok":
            lat, lon, q = c["lat"], c["lon"], 0
            mun, city = c.get("m"), c.get("w")
        else:
            f = self.cache.get("pc6|" + pc6) if pc6 else None
            if f and f.get("s") == "ok":
                lat, lon, q = f["lat"], f["lon"], 1
                mun, city = f.get("m"), f.get("w")
            elif pc4 in self.pc4:
                lat, lon, q = self.pc4[pc4]["lat"], self.pc4[pc4]["lon"], 2
                mun, city = self.pc4m.get(pc4), None
            else:
                lat, lon, q, mun, city = None, None, 3, None, None
        if not mun:
            mun = self.gemnames.get(s["gemnr"]) or duo.title_nl(s["gem_raw"])
        if not city:
            city = duo.title_nl(s["city_raw"])
        if lat is not None:
            lat, lon = round(lat, 5), round(lon, 5)
        return lat, lon, q, mun, city
