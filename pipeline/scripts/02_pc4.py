"""Step 2: PC4 centroids from CBS postcode4 (PDOK OGC API, CC BY 4.0) + municipality per PC4.

Checkpointed:
  raw/pc4_geom.jsonl  one line per PC4 {"pc4","lat","lon"} plus {"_next": url} after every page
  raw/pc4_muni.jsonl  one line per PC4 {"pc4","m"} (municipality of the PC6 nearest the centroid)
Both resume on restart. Only the centroid is kept from the (large) polygon geometry.
"""
import os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, JsonlAppender, Throttle, http_get_json, read_jsonl

YEAR = 2024  # latest jaarcode in the CBS postcode4 file with full coverage (2025 returned 0 features)
START = ("https://api.pdok.nl/cbs/postcode4/ogc/v1/collections/postcode4/items"
         "?f=json&limit=250&jaarcode=%d" % YEAR)
LS = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/reverse"


def ring_area_centroid(ring):
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    if a == 0:
        return 0.0, ring[0][0], ring[0][1]
    return a / 2.0, cx / (3.0 * a), cy / (3.0 * a)


def in_ring(x, y, ring):
    ins = False
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            ins = not ins
    return ins


def centroid(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    # shift to local coords: scale lon by cos(lat) so areas are roughly right
    import math
    lat0 = polys[0][0][0][1]
    k = math.cos(math.radians(lat0))
    tot = sx = sy = 0.0
    best = None
    for poly in polys:
        outer = [(x * k, y) for x, y in poly[0]]
        a, cx, cy = ring_area_centroid(outer)
        w = abs(a)
        holes = 0.0
        for h in poly[1:]:
            ha, hx, hy = ring_area_centroid([(x * k, y) for x, y in h])
            holes += abs(ha)
            sx -= abs(ha) * hx
            sy -= abs(ha) * hy
            tot -= abs(ha)
        sx += w * cx
        sy += w * cy
        tot += w
        if best is None or w > best[0]:
            best = (w, poly)
    cx, cy = sx / tot, sy / tot
    # make sure the point lies inside some polygon; otherwise use midpoint of the longest
    # horizontal chord through the largest polygon at the centroid latitude
    for poly in polys:
        if in_ring(cx, cy, [(x * k, y) for x, y in poly[0]]) and not any(
                in_ring(cx, cy, [(x * k, y) for x, y in h]) for h in poly[1:]):
            return cx / k, cy
    ring = [(x * k, y) for x, y in best[1][0]]
    xs = []
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        if (y0 > cy) != (y1 > cy):
            xs.append((x1 - x0) * (cy - y0) / (y1 - y0) + x0)
    xs.sort()
    bestw, mid = -1, cx
    for i in range(0, len(xs) - 1, 2):
        if xs[i + 1] - xs[i] > bestw:
            bestw, mid = xs[i + 1] - xs[i], (xs[i] + xs[i + 1]) / 2
    return mid / k, cy


def geometry_step():
    path = os.path.join(RAW, "pc4_geom.jsonl")
    rows = read_jsonl(path)
    done = {r["pc4"] for r in rows if "pc4" in r}
    nxt = START
    finished = False
    for r in rows:
        if "_next" in r:
            nxt = r["_next"]
        if r.get("_done"):
            finished = True
    if finished:
        print("geometry: already complete,", len(done), "PC4")
        return
    ap = JsonlAppender(path)
    th = Throttle(1)
    while nxt:
        th.wait()
        d = http_get_json(nxt, timeout=180)
        for f in d["features"]:
            pc4 = "%04d" % f["properties"]["postcode"]
            if pc4 in done:
                continue
            lon, lat = centroid(f["geometry"])
            ap.write({"pc4": pc4, "lat": round(lat, 5), "lon": round(lon, 5)})
            done.add(pc4)
        nxt = next((l["href"] for l in d["links"] if l["rel"] == "next"), None)
        ap.write({"_next": nxt} if nxt else {"_done": 1})
        print("geometry page ok, total", len(done), flush=True)
    ap.close()


def muni_step():
    gpath = os.path.join(RAW, "pc4_geom.jsonl")
    cents = {r["pc4"]: r for r in read_jsonl(gpath) if "pc4" in r}
    mpath = os.path.join(RAW, "pc4_muni.jsonl")
    done = {r["pc4"] for r in read_jsonl(mpath)}
    todo = [p for p in sorted(cents) if p not in done]
    print("municipality lookups to do:", len(todo), flush=True)
    ap = JsonlAppender(mpath)
    th = Throttle(2)
    for i, p in enumerate(todo):
        c = cents[p]
        q = urllib.parse.urlencode({"lon": c["lon"], "lat": c["lat"], "type": "postcode", "rows": 6,
                                    "fl": "postcode,gemeentenaam"})
        th.wait()
        d = http_get_json(LS + "?" + q)
        docs = d.get("response", {}).get("docs", [])
        m = None
        for doc in docs:
            if str(doc.get("postcode", "")).startswith(p):
                m = doc.get("gemeentenaam")
                break
        if m is None and docs:
            m = docs[0].get("gemeentenaam")
        ap.write({"pc4": p, "m": m})
        if i % 200 == 0:
            print("muni", i, "/", len(todo), flush=True)
    ap.close()


if __name__ == "__main__":
    geometry_step()
    muni_step()
