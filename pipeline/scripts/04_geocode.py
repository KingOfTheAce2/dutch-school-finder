"""Step 4: geocode school addresses with PDOK Locatieserver (checkpointed, resumable).

Cache: raw/geocode_cache.jsonl, one line per finished unit, flushed + fsynced immediately.
  address unit : {"k":"2716PH|22|","s":"ok","lat":..,"lon":..,"m":"Zoetermeer","w":"Zoetermeer","x":1}
                 {"k":..,"s":"nf"}                      (no address with that postcode + number)
  pc6 unit     : {"k":"pc6|2716PH","s":"ok",...} / "nf"  (fallback centroid, run for address misses)
Restart skips everything already in the cache. Use --limit N for a small test batch.
Each address is looked up with q=postcode:<PC6> AND huisnummer:<n> (fq=type:adres) and the result is
verified (postcode + number must match) because the plain free-text query silently returns near misses
(e.g. "2716PH 13" returns number 22).
"""
import argparse, os, re, sys, threading, urllib.parse
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, JsonlAppender, Throttle, http_get_json, read_jsonl
import duo

LS = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
FL = "weergavenaam,centroide_ll,gemeentenaam,woonplaatsnaam,postcode,huisnummer,huisletter,huisnummertoevoeging"


def parse_point(s):
    m = re.match(r"POINT\(([-0-9.]+) ([-0-9.]+)\)", s or "")
    return (float(m.group(2)), float(m.group(1))) if m else None


def query(q, fq, rows):
    url = LS + "?" + urllib.parse.urlencode({"q": q, "fq": fq, "rows": rows, "fl": FL})
    return http_get_json(url, timeout=30).get("response", {}).get("docs", [])


def lookup_address(pc6, n, suf):
    docs = query("postcode:%s AND huisnummer:%d" % (pc6, n), "type:adres", 30)
    docs = [d for d in docs if str(d.get("postcode", "")).upper() == pc6 and d.get("huisnummer") == n]
    if not docs:
        return {"s": "nf"}
    best, exact = docs[0], 0
    for d in docs:
        dsuf = (str(d.get("huisletter", "")) + str(d.get("huisnummertoevoeging", ""))).upper()
        dsuf = re.sub(r"[^A-Z0-9]", "", dsuf)
        if dsuf == suf:
            best, exact = d, 1
            break
    else:
        if not suf:  # prefer the plain number if the school has no suffix
            for d in docs:
                if not d.get("huisletter") and not d.get("huisnummertoevoeging"):
                    best = d
                    break
    p = parse_point(best.get("centroide_ll"))
    if not p:
        return {"s": "nf"}
    return {"s": "ok", "lat": round(p[0], 6), "lon": round(p[1], 6), "m": best.get("gemeentenaam"),
            "w": best.get("woonplaatsnaam"), "x": exact}


def lookup_pc6(pc6):
    docs = query("postcode:%s" % pc6, "type:postcode", 5)
    docs = [d for d in docs if str(d.get("postcode", "")).upper() == pc6]
    if not docs:
        return {"s": "nf"}
    p = parse_point(docs[0].get("centroide_ll"))
    if not p:
        return {"s": "nf"}
    return {"s": "ok", "lat": round(p[0], 6), "lon": round(p[1], 6), "m": docs[0].get("gemeentenaam"),
            "w": docs[0].get("woonplaatsnaam")}


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--limit", type=int, default=0, help="stop after N new units (test batch)")
    ap_.add_argument("--rate", type=float, default=4.0, help="requests per second")
    ap_.add_argument("--workers", type=int, default=3, help="concurrent in-flight requests (rate is still capped)")
    a = ap_.parse_args()

    schools = duo.load_po_schools() + duo.load_vo_schools()
    keys = sorted({k for k in (duo.geo_key(s) for s in schools) if k})
    path = os.path.join(RAW, "geocode_cache.jsonl")
    cache = {r["k"]: r for r in read_jsonl(path) if "k" in r}
    todo = [k for k in keys if k not in cache]
    print("address keys:", len(keys), "done:", len(keys) - len(todo), "todo:", len(todo), flush=True)
    ap = JsonlAppender(path)
    th = Throttle(a.rate)
    lock = threading.Lock()

    def paced(fn, *args):
        with lock:  # one shared request clock; workers only overlap the network latency
            th.wait()
        return fn(*args)

    n_new = 0
    B = 24  # small batches: at most one batch is re-done after a crash
    stop = False
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for b in range(0, len(todo), B):
            batch = todo[b:b + B]
            if a.limit:
                batch = batch[:max(0, a.limit - n_new)]
                if not batch:
                    stop = True
                    break
            futs = []
            for k in batch:
                pc6, n, suf = k.split("|")
                futs.append((k, ex.submit(paced, lookup_address, pc6, int(n), suf)))
            for k, f in futs:
                r = f.result()
                r["k"] = k
                ap.write(r)
                cache[k] = r
                n_new += 1
            if (b // B) % 4 == 0:
                print("address", n_new, "new,", len(todo) - b - len(batch), "left", flush=True)
        if not stop:
            miss = sorted({k.split("|")[0] for k in keys if cache.get(k, {}).get("s") != "ok"})
            todo2 = [p for p in miss if ("pc6|" + p) not in cache]
            print("pc6 fallback units:", len(miss), "todo:", len(todo2), flush=True)
            for b in range(0, len(todo2), B):
                batch = todo2[b:b + B]
                if a.limit:
                    batch = batch[:max(0, a.limit - n_new)]
                    if not batch:
                        break
                futs = [(p, ex.submit(paced, lookup_pc6, p)) for p in batch]
                for p, f in futs:
                    r = f.result()
                    r["k"] = "pc6|" + p
                    ap.write(r)
                    n_new += 1
                print("pc6", b + len(batch), "/", len(todo2), flush=True)
    ap.close()
    print("done; new units this run:", n_new, flush=True)


if __name__ == "__main__":
    main()
