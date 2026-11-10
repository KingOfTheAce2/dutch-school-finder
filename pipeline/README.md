# Schoollijn open-data pipeline

Precomputes compact JSON for the static Schoollijn page. The browser only reads the files in `out/` (schools_po, schools_vo, pc4, meta, features); nothing is fetched at runtime.

Allowed sources only: DUO Open Onderwijsdata, CBS, PDOK / Kadaster. Scholen op de kaart is not used (its terms forbid storage and text/data mining).

`out/features.json` adds association lists and school websites (steps 10 to 14, see below for sources and terms); those steps are not part of `build_all.py` because they need a long network crawl.

## Run

```
python -I scripts/build_all.py                 # everything (downloads, PDOK lookups, builds, validation)
python -I scripts/build_all.py --skip-geocode  # rebuild out/ from the caches in raw/
```

Always run with `-I` (isolated mode): the files in `raw/` are untrusted downloads. `scripts/` holds our code only; each script adds its own directory to `sys.path` explicitly.

| Step | Script | Notes |
|---|---|---|
| 1 | `01_download.py` | DUO CSVs into `raw/`, writes `raw/MANIFEST.json` (URL, size, sha256). Skips files already present. |
| 2 | `02_pc4.py` | CBS Postcode4 polygons (PDOK OGC API) reduced to one centroid per PC4, then municipality per PC4. Checkpoints: `raw/pc4_geom.jsonl` (per page), `raw/pc4_muni.jsonl` (per PC4). |
| 4 | `04_geocode.py` | PDOK Locatieserver lookups for every school address. Checkpoint: `raw/geocode_cache.jsonl` (flush + fsync per unit, batches of 24, resumes by skipping cached keys). `--limit N` runs a test batch. |
| 5 | `05_build_po.py` | `out/schools_po.json` |
| 6 | `06_build_vo.py` | `out/schools_vo.json` |
| 7 | `07_build_pc4.py` | `out/pc4.json` |
| 8 | `08_build_meta.py` | `out/meta.json` |
| 9 | `09_validate.py` | Prints coverage, bounding-box and spot checks. |

Helpers: `common.py` (paths, retrying HTTP, JSONL appender), `duo.py` (CSV parsers and cleaning), `geo.py` (coordinate fallback chain).

`raw/` is git-ignored (`data/.gitignore`). Politeness: about 3.5 requests per second to PDOK, retry with exponential backoff on 429/5xx.

## Common conventions

- Each file is an envelope with a `cols` array and `rows` as arrays in that column order (short keys, no repeated field names).
- `null` means unknown or suppressed. DUO hides counts below 5 (`<5` in the CSV). We never turn a suppressed cell into a number and never recover it by subtraction.
- `lat`, `lon`: WGS84, 5 decimals.
- `g` = geocoding quality: `0` exact BAG address, `1` PC6 centroid fallback, `2` PC4 centroid fallback, `3` no coordinates.
- `prov` = index into the `prov` array (`-1` = unknown). `den` = index into the `den` array (denomination, DUO "richting").
- `web` has no scheme; prepend `https://`. It is validated against a conservative pattern, but still insert it with `textContent`/`setAttribute`, never as HTML. Treat every string as untrusted text.
- `pupils` is the sum of all exact cells. If `pupils_lb` is `1`, at least one cell was suppressed (1 to 4 pupils), so `pupils` is a lower bound; show it as "at least N".
- Names, streets and cities come from DUO and PDOK as-is; city and municipality prefer the PDOK/BAG spelling.

## out/schools_po.json

Every basisonderwijs location (DUO "alle schoolvestigingen basisonderwijs") plus every speciaal basisonderwijs location (the SBAO rows of DUO "alle vestigingen sbo, so en vso"; `sbo = 1`).

```
{ "v":1, "years":{...}, "cols":[...], "prov":[...], "den":[...], "levels":[...], "rows":[[...], ...] }
```

| col | meaning |
|---|---|
| `id` | BRIN6, i.e. BRIN + vestigingscode (e.g. `21AF00`) |
| `name`, `addr`, `pc`, `city`, `mun` | name, street + number, postcode (6 chars, no space), city, municipality |
| `lat`, `lon`, `g` | coordinates and quality code |
| `prov`, `den` | indices, see above |
| `sbo` | 1 = speciaal basisonderwijs |
| `pupils`, `pupils_lb` | pupils, all groups (leerjaar 1-8), 1 October 2025 (school year 2025/26) |
| `adv` | schooladvies of leavers 2024/25: `[n, s, shares]` or `null` (no row in DUO file). `n` = leavers in unsuppressed cells, `s` = number of suppressed cells (of 12), `shares` = 12 numbers in percent of `n` (one decimal) in the order of `levels`, `null` where the cell is suppressed. `shares` is `null` when `n` is 0. |
| `web` | website or `null` |

`levels`: VSO, PRO, VMBO_B, VMBO_B_K, VMBO_K, VMBO_K_GT, VMBO_GT, VMBO_GT_HAVO, HAVO, HAVO_VWO, VWO, ADVIES_NIET_MOGELIJK.

Caveat for `adv`: when `s > 0` the shares are of the disclosed leavers only and overstate the visible levels (suppressed cells hold 1 to 4 pupils each). Show them only with a "based on at least n pupils, some small groups hidden" note, or hide them when `s` is large. Almost every school has some suppressed cell; see `meta.json` and the report for how many are clean.

## out/schools_vo.json

Every VO location in the DUO address file (including nevenvestigingen, ISK and VAVO-only locations that have no pupil row).

Extra columns: `tracks` (bitmask), `exam`, `st` (DUO "onderwijsstructuur" string from the address file, e.g. `VBO/MAVO/HAVO/VWO`).

`tracks` bits (also in `bits` inside the file): `pro` 1, `bb` 2, `kb` 4, `gl` 8, `tl` 16, `havo` 32, `vwo` 64, `gym` 128, `ath` 256, `ib` 512, `ess` 1024.

- Derived from DUO "leerlingen VO per vestiging naar onderwijstype" 2025: a track counts as offered when the location has a row for it with at least one pupil (or a suppressed `<5` cell). Brugjaar rows (year 1-2) add the tracks named in their programme name (e.g. "VMBO-GL/TL/HAVO voorbereidende leerjaren" adds gl, tl, havo). Rows "uitbest. aan VAVO" are excluded.
- `gym` / `ath`: the VWO programme name contains gymnasium / atheneum (also GYM / ATH profile rows). A school can have both; neither flag means DUO did not name the stream.
- `ib`: International Baccalaureate programmes (DP, CP, MYP). `ess`: European Secondary School. Not a complete list of international schools (most are not publicly funded and are not in DUO).
- `tracks = 0` means no pupil rows (not necessarily "no tracks"): use `st` as a fallback.

`exam`: `null` or a list, one entry per track with exam data, `[track, candidates, pass_pct, partial]`, track in `bb kb gl tl havo vwo` (school year 2024/25, final-year candidates). DUO reports exams per department/profile; we add the exact rows up. `candidates` and `pass_pct` are `null` when every row of the track is suppressed. `partial = 1` means some rows of that track were suppressed (1 to 4 candidates each) and left out of the totals, so the figures cover the disclosed rows only. Praktijkonderwijs has no exam. Suggested display rule (from the data inventory): show pass rate only when `candidates >= 30`.

`pupils`: all years, VAVO excluded, 1 October 2025 (provisional DUO figure).

## out/pc4.json

`{ "1011": [52.3737, 4.9005, "Amsterdam"], ... }`: one entry per PC4 in the CBS Postcode4 file (jaarcode 2024). Coordinates are the area centroid of the CBS polygon (4 decimals; moved inside the polygon if the centroid falls outside). The municipality is that of the postcode (PC6) nearest to the centroid, from PDOK Locatieserver; PC4 areas that straddle a municipal border are labelled by the municipality of the centroid only. Postcode-4 areas without inhabitants or addresses may be missing from CBS.

Page logic: take the first four digits of the user's postcode, look up the entry, compute distances to schools in the browser (haversine). This is a centroid, so accuracy is a few hundred metres to a few kilometres in rural areas.

## out/meta.json

Data years per source, generation date, record counts, geocoding match rates (`geocoding.address_match_rate` and the fallback counts per school file) and the attribution block (`attribution`: source, text, licence, licence_url, url) for the Data sources page, plus a short disclaimer.

## out/features.json (school concepts, international features, open days)

Enrichment of the DUO ids with features DUO does not have. Built by steps 10 to 14 (below), generated 2026-10-16.

```
{ "v":1, "generated", "flags":{key:label}, "confidence":{level:meaning},
  "schools": { "<DUO id>": { "flags":[...], "open_days":[...], "evidence":{...}, "confidence":{...}, "corroborated":[...]? } } }
```

The id map is under `schools` (the envelope keeps the file consistent with the others). Only ids with at least one flag or open day are present.

| flag | meaning | main source |
|---|---|---|
| `tto` | bilingual secondary education (tweetalig onderwijs) | Nuffic tto network list, school sites |
| `tbo` | bilingual primary (tweetalig basisonderwijs) | school sites only (1 school) |
| `ib` | International Baccalaureate (DP, MYP, PYP, CP) | DUO IB programme rows, DIS list, school sites |
| `technasium` | Technasium | Stichting Technasium network pages |
| `montessori`, `dalton`, `jenaplan`, `vrije_school` | education concept | association lists NMV, NDV, NJPV, Vereniging van vrijescholen |
| `international` | international department or school (IGBO/IGVO, international stream) | DIS and SIO lists, school sites |
| `newcomer` | newcomer class (ISK, schakelklas, taalklas, kopklas, EOA) | DUO location names, school sites |

- `evidence[flag] = [source_url, snippet (<= 150 chars), "list" | "site", checked_date]`: the best source per flag (list beats site). `corroborated` names flags confirmed by both a list and a site.
- `confidence[flag]`: `high` = official or association list entry matched to the DUO id (or a DUO field); `medium` = keyword in a title/heading/running text of a school page, or a list entry matched to several locations of the same school group (tto); `low` = keyword only in a menu or link, or on a website that serves several DUO locations (school group or board site), so it may belong to a sibling location. A UI should show `low` only as "mentioned on the school group's site" or hide it.
- `open_days`: `[{date (ISO), label, url, school_year, inferred?, shared_site?}]`. Past dates (before the build date) are dropped; at most 12 per school. `school_year` is the school year in which the event takes place (winter events 2026/27 are normally for intake in 2027/28). `inferred: true` = the page gave no year and the next occurrence of day and month was taken (a weekday written before the date has to agree with the calendar). `shared_site: true` = the page belongs to a site that serves several DUO locations. Labels are heuristic (nearest keyword before the date); dates go stale quickly, re-run steps 12 and 13 shortly before publication and always link to the source page.

### Pipeline (all `python -I`; needs beautifulsoup4, lxml, rapidfuzz in the interpreter)

| Step | Script | Notes |
|---|---|---|
| 10 | `10_fetch_lists.py`, `10_parse_lists.py` | Snapshots of the association lists in `raw/lists/` (`MANIFEST.json`: URL, date, sha256), parsed to `raw/lists_parsed.json`. |
| 11 | `11_match_lists.py` | Fuzzy match to DUO ids (postcode, website host, city, normalised name; tto and technasium entries must fit the location's tracks). Doubtful pairs were decided by hand in `scripts/list_overrides.json`. Writes `review/lists_unmatched.json` and `review/lists_doubtful.json` (entries that are not in DUO, mostly private international schools, childcare, and pairs we did not dare to link). |
| 12 | `12_crawl_sites.py` | Polite crawl of school websites, checkpoint `raw/crawl_checkpoint.jsonl` (one line per website, flush + fsync, finished sites are skipped on restart). `--limit N --seed S --checkpoint F` for test batches. |
| 13 | `13_build_features.py` | Combines lists, DUO fields and crawl into `out/features.json`; applies the acceptance rules and drops past open days. |
| 14 | `14_features_meta.py` | Writes the `features` block of `out/meta.json` (sources, terms, retrieval dates, match rates, crawl coverage). `08_build_meta.py` keeps that block when it rebuilds `meta.json`. |

### Lists used (retrieved 2026-10-16) and their terms

| Flag | Source | Entries | Matched to DUO | Terms |
|---|---|---|---|---|
| tto | Nuffic, "Alle tto-scholen in Nederland" (nuffic.nl) | 122 | 106 | Site content CC BY-NC 4.0: attribution, non-commercial only |
| technasium | Stichting Technasium, 19 regional network pages | 100 | 88 | "Creative commons guidelines": no commercial use, attribution, no adaptation without permission. We keep the fact of membership and the page URL only; ask before commercial or derivative use |
| montessori | Nederlandse Montessori Vereniging, school finder JSON | 217 (incl. childcare) | 178 | none stated |
| dalton | Nederlandse Dalton Vereniging, scholenzoeker JSON | 361 | 333 | none stated |
| jenaplan | Nederlandse Jenaplan Vereniging, school map | 187 | 169 | none stated |
| vrije_school | Vereniging van vrijescholen, "Onze scholen" | 139 school records | 114 | none stated |
| international, ib | Dutch International Schools (DIS) "Find a school" | 49 | 17 | none stated |
| international | SIO "Find a school by city" | 57 | 10 | none stated |

"None stated" means no licence or terms text was found on the site (checked 2026-10-16), robots.txt allows the pages, and the content is public factual contact data. We attribute and link to the source, but the associations should be asked before the data is redistributed as a dataset.

Not used: LOWAN (its disclaimer forbids copying; fetched once to inspect, then deleted, nothing derived from it is in the output; newcomer flags come from DUO location names and school sites instead; ask LOWAN for permission to use their lists), ibo.org (HTTP 403 to non-browser clients, terms restrict automated collection), tto.nl (HTTP 403), Scholen op de kaart (terms forbid it, see above).

### Website crawl

User-Agent `SchoollijnBot/0.1 (research; contact via site)`. robots.txt is obeyed (including Crawl-delay, capped at 10 s; a robots.txt that answers 401, 403 or 5xx counts as disallow). At most 1 request per second per registrable domain, 8 sites in parallel, 15 s timeout, 2 MB per page, HTML only. Per site: homepage plus at most 5 internal pages whose link text or path matches keywords (open dag, kennismaken, tto, tweetalig, bilingual, IB, technasium, gymnasium, montessori, dalton, jenaplan, ISK, schakelklas, aanmelden and a few more). Scope: all 1,235 VO locations with a website (856 crawl units) plus 347 primary locations (342 units) whose name or website hints at a concept or international stream, or that appear on the DIS/SIO lists. Only facts are stored (flags, dates, source URL, snippet of at most 150 characters); pages are parsed with bs4 and regular expressions and never executed, instructions inside pages are ignored.

Acceptance rules for site flags: concept words (montessori, dalton, jenaplan, vrije school) need the term in a page title, heading or URL, or at least 3 times in running text (menus often list sibling schools); other flags need the term in a title, heading, URL, running text or a menu. A mention directly after "geen", "niet" or "zonder" is ignored. Acronyms (TTO, ISK, EOA) are case sensitive. Sites that fail on TLS certificate errors, DNS errors or HTTP errors are skipped and counted in `meta.json` (`features.site_crawl`).

## Licences

- DUO Open Onderwijsdata: DUO states CC0 on its own site, the data catalogue labels the files CC BY 4.0. We treat everything as CC BY 4.0 and attribute.
- CBS Postcode4 (via PDOK OGC API): CC BY 4.0.
- Kadaster BAG via PDOK Locatieserver: open data (Public Domain Mark in the data.overheid.nl catalogue); credited anyway.

## Known gaps

- Inspectie quality ratings are not included (the DUO copy is from 2018, a current open file was not found).
- Features (tto, IB, concepts, international, newcomer, open days) are in `out/features.json` and are indications from lists and school websites, not official classifications; coverage is incomplete (see the match rates above) and open days go stale. Private international schools are mostly not in DUO and therefore not in the output (see `review/lists_unmatched.json`).
- Primary schooladvies data is 2024/25 (latest DUO file); primary pupils are 2025/26.
- DUO's primary pupil file lists about 87 BO locations that are not in the BO address file; they are skipped (no address).
- Postcode-only fallback when an address is not found in the BAG (see `g`).
