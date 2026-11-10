"""Step 14: merge a `features` block into out/meta.json (sources, terms, retrieval dates, match rates,
crawl coverage, counts per flag). Idempotent; run after 08_build_meta.py and 13_build_features.py. `python -I`."""
import os, sys, json, collections, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, OUT, read_jsonl, write_json_atomic

RET = "2026-10-16"

LISTS = [
    {"key": "tto", "flag": "tto", "source": "Nuffic, Netwerk tto: 'Alle tto-scholen in Nederland'",
     "url": "https://www.nuffic.nl/onderwijssectoren/voortgezet-onderwijs/tweetalig-onderwijs/alle-tto-scholen-in-nederland",
     "format": "HTML list (city, school, tto levels); no addresses",
     "terms": "Nuffic site content is CC BY-NC 4.0 (https://www.nuffic.nl/over-nuffic/algemene-voorwaarden/copyright): attribution required, non-commercial reuse only.",
     "reuse_ok": "yes, attribution + non-commercial only"},
    {"key": "technasium", "flag": "technasium", "source": "Stichting Technasium, regional network pages (Aangesloten scholen)",
     "url": "https://www.technasium.nl/netwerk/<regio>/ (19 pages, listed in https://www.technasium.nl/netwerk-sitemap.xml)",
     "format": "HTML (school, street, postcode, city, website)",
     "terms": "https://www.technasium.nl/privacy-gebruik/ item 5: content under Creative Commons guidelines: no commercial use, attribution required, no adaptation without prior permission. We store only the fact of membership plus the page URL; ask Stichting Technasium before any commercial or derivative use.",
     "reuse_ok": "restricted: attribution, non-commercial, no adaptation without permission"},
    {"key": "montessori", "flag": "montessori", "source": "Nederlandse Montessori Vereniging, 'Vind een montessori-instelling' (WP Store Locator JSON)",
     "url": "https://montessori.nl/professionals/vind-een-montessori-instelling/",
     "format": "JSON from the page's own store-locator endpoint (admin-ajax.php?action=store_search), includes childcare and nursery locations (rejected at matching)",
     "terms": "No licence or terms statement found on montessori.nl (checked 2026-10-16); robots.txt allows the endpoint. Treated as public factual contact data; attribution given.",
     "reuse_ok": "unspecified"},
    {"key": "dalton", "flag": "dalton", "source": "Nederlandse Dalton Vereniging, Scholenzoeker (WP Store Locator JSON)",
     "url": "https://dalton.nl/over-dalton/scholenzoeker/",
     "format": "JSON from admin-ajax.php?action=store_search (361 locations, PO and VO)",
     "terms": "No licence or terms statement found on dalton.nl (checked 2026-10-16); robots.txt allows the endpoint. Treated as public factual contact data; attribution given.",
     "reuse_ok": "unspecified"},
    {"key": "jenaplan", "flag": "jenaplan", "source": "Nederlandse Jenaplan Vereniging, school map on /vereniging",
     "url": "https://jenaplan.nl/vereniging",
     "format": "init_markers array embedded in the page (name, address, postcode, website)",
     "terms": "No licence or terms statement found on jenaplan.nl (only a privacy statement; no robots.txt, checked 2026-10-16). Treated as public factual contact data; attribution given.",
     "reuse_ok": "unspecified"},
    {"key": "vrije", "flag": "vrije_school", "source": "Vereniging van vrijescholen, 'Onze scholen'",
     "url": "https://www.vrijescholen.nl/onze-scholen",
     "format": "school records embedded in the page (title, street, postcode, city, website, type); only primary, secondary, special and 'initiatief' records used",
     "terms": "No licence or terms statement found on vrijescholen.nl (checked 2026-10-16); robots.txt allows /. Treated as public factual contact data; attribution given.",
     "reuse_ok": "unspecified"},
    {"key": "dis", "flag": "international (+ib)", "source": "Dutch International Schools (DIS), 'Find a school'",
     "url": "https://www.dutchinternationalschools.nl/schools/",
     "format": "map markers embedded in the page (name, address, postcode, website, programme categories IPC/IB-MYP/IB-DP/British)",
     "terms": "No licence or terms statement found (checked 2026-10-16); robots.txt allows the page. Treated as public factual data; attribution given.",
     "reuse_ok": "unspecified"},
    {"key": "sio", "flag": "international", "source": "SIO (former Stichting Internationaal Onderwijs), 'Find a school by city'",
     "url": "https://sio.nl/information-for-families/find-a-school-by-city/",
     "format": "HTML list (city, school name, website); no addresses",
     "terms": "No licence or terms statement found (checked 2026-10-16); robots.txt allows the page. Treated as public factual data; attribution given.",
     "reuse_ok": "unspecified"},
]

NOT_USED = [
    {"source": "LOWAN (newcomer education locations, PO and VO)", "url": "https://www.lowan.nl/",
     "reason": "Disclaimer (https://www.lowan.nl/po/disclaimer/) forbids copying, downloading or distributing site information without written permission. Fetched once to inspect (titles only, no addresses), then deleted; nothing derived from it is in features.json. Newcomer flags come from DUO location names and school websites instead. Ask LOWAN for permission to use their lists."},
    {"source": "ibo.org IB school finder", "url": "https://www.ibo.org/programmes/find-an-ib-school/",
     "reason": "Answers HTTP 403 to non-browser clients and the IBO terms restrict automated collection; not attempted. IB flags come from DUO (IB programme rows), the DIS list and school websites."},
    {"source": "tto.nl", "url": "https://www.tto.nl/", "reason": "Answers HTTP 403; the Nuffic page above publishes the same network list."},
    {"source": "Scholen op de kaart", "url": "https://scholenopdekaart.nl/", "reason": "Terms forbid storage and text/data mining (see README)."},
]


def main():
    mp = os.path.join(OUT, "meta.json")
    meta = json.load(open(mp, encoding="utf-8"))
    lm = json.load(open(os.path.join(RAW, "list_matches.json"), encoding="utf-8"))
    for L in LISTS:
        st = lm["stats"][L["key"]]
        L["retrieved"] = RET
        L["entries"] = st["entries"]
        L["matched_entries"] = st["matched"]
        L["doubtful_entries"] = st["doubtful"]
        L["unmatched_entries"] = st["unmatched"]
        L["match_rate"] = round(st["matched"] / st["entries"], 3) if st["entries"] else None
    feats = json.load(open(os.path.join(OUT, "features.json"), encoding="utf-8"))
    cnt = collections.Counter()
    for it in feats["schools"].values():
        for f in it["flags"]:
            cnt[f] += 1
    recs = {}
    for r in read_jsonl(os.path.join(RAW, "crawl_checkpoint.jsonl")):
        recs[r["host"]] = r
    st = collections.Counter(r["status"] for r in recs.values())
    pages = sum(len(r.get("pages") or []) for r in recs.values())
    errs = collections.Counter()
    for r in recs.values():
        for e in r.get("errors") or []:
            errs[e.split(":")[0].split(" ")[0][:20]] += 1
    meta["features"] = {
        "generated": datetime.date.today().isoformat(),
        "file": "features.json",
        "flags": feats["flags"],
        "counts_schools_per_flag": dict(cnt),
        "schools_with_features": len(feats["schools"]),
        "schools_with_open_days": sum(1 for i in feats["schools"].values() if i["open_days"]),
        "lists": LISTS,
        "not_used": NOT_USED,
        "site_crawl": {
            "user_agent": "SchoollijnBot/0.1 (research; contact via site)",
            "date": RET,
            "robots_txt": "obeyed (also Crawl-delay, capped at 10 s); unreadable 401/403/5xx robots.txt treated as disallow",
            "rate": "max 1 request per second per registrable domain, 8 hosts in parallel",
            "pages_per_site": "homepage + at most 5 internal pages chosen by keyword",
            "hosts": len(recs), "hosts_by_status": dict(st), "pages_fetched": pages,
            "page_errors_by_type": dict(errs),
            "stored": "feature flags and open-day dates with source URL and snippet of at most 150 characters; no page text or images",
        },
        "confidence": feats["confidence"],
        "open_days_note": "school_year is the school year in which the event takes place (e.g. 2026/27); dates in winter 2026/27 are normally for intake in 2027/28. inferred=true means the page gave no year and the next occurrence of day and month was assumed. Past dates are dropped at build time. Re-run 12/13 close to publication; dates go stale.",
        "disclaimer": "Feature flags are indications from association lists and school websites, not official classifications. Verify with the school. Not affiliated with the organisations named.",
    }
    write_json_atomic(mp, meta)
    print("meta.json features block written")


if __name__ == "__main__":
    main()
