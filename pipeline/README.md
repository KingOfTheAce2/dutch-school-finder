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
| 4 | `04_geocode.py` | PDOK Locatieserver lookups for every school address (PO, SBO, SO/VSO and VO). Checkpoint: `raw/geocode_cache.jsonl` (flush + fsync per unit, batches of 24, resumes by skipping cached keys). `--limit N` runs a test batch. |
| 5 | `05_build_po.py` | `out/schools_po.json` |
| 5b | `05b_build_so.py` | `out/schools_so.json` (special education SO/VSO) |
| 6 | `06_build_vo.py` | `out/schools_vo.json` |
| 7 | `07_build_pc4.py` | `out/pc4.json` |
| 8 | `08_build_meta.py` | `out/meta.json` |
| 15 | `15_download_detail.py` | Extra DUO files (pupil history, doorstroomtoets, advice history, distance, exam history, pupil postcodes) and the Inspectie ODS into `raw/`, MANIFEST entries, skips files present. |
| 16 | `16_build_detail_po.py` | `out/detail_po.json` |
| 17 | `17_build_detail_vo.py` | `out/detail_vo.json` |
| 18 | `18_build_inspection.py` | `out/inspection.json` |
| 9 | `09_validate.py` | Prints coverage, bounding-box and spot checks, plus coverage/consistency checks for the three detail files (exits non-zero on failure). Runs after step 8 in `build_all.py`. |

Helpers: `xlsx.py` (stdlib .xlsx/.ods readers for DUO/Inspectie spreadsheets), `common.py` (paths, retrying HTTP, JSONL appender), `duo.py` (CSV parsers and cleaning), `geo.py` (coordinate fallback chain).

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

## out/schools_so.json

Special education: every SO (speciaal onderwijs, ages 4-12) and VSO (voortgezet speciaal onderwijs) location of DUO "alle vestigingen sbo, so en vso" (639 locations). SBAO stays in schools_po (`sbo = 1`). Same envelope and the same first 16 columns as schools_po (`sbo` is always 0, `adv` always null: there is no schooladvies in SO), plus:

| col | meaning |
|---|---|
| `so_type` | `"SO"`, `"VSO"` or `"SO/VSO"`. Derived from the DUO column ONDERWIJS ("SO ZMLK + VSO ZMLK ..."; RP-SO and RP-VSO parts count as SO and VSO), not from the pupil file |
| `cl` | cluster 1 to 4 when DUO gives exactly one, else `null` (9 locations are `3/4`: see `cls`). 1 visual, 2 hearing and severe speech/language problems, 3 physical or intellectual disability and long-term illness, 4 behavioural or psychiatric problems (also in the top-level `clusters` object) |
| `cls` | list of all clusters, e.g. `[3,4]`; `null` when DUO leaves it blank |
| `pso`, `pvso` | pupils in the SO part and in the VSO part, 1 October 2025. `null` = no row, or only suppressed cells |

`pupils` is the sum of the exact SO and VSO cells (all ages), `pupils_lb = 1` when some age cell was suppressed (`<5`), so it is a lower bound. A location with `pupils = null` (44 of 639) has no row in the DUO pupil file. `levels` is an empty array. Source: DUO "leerlingen po naar soort po, cluster en leeftijd" 2025-2026 (`raw/so_leerlingen_2025-2026.csv`, one row per vestiging and type, age columns) and the address file. The ids of schools_so never occur in schools_po. The file is geocoded by the same checkpointed step 4 and the same cache.

Not available as open data per vestiging: ondersteuningsprofiel, toelaatbaarheid/TLV criteria, VSO uitstroom per school (DUO publishes uitstroom only per samenwerkingsverband).

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


## Detail files (steps 15 to 18)

Per-school detail for the school page, keyed by BRIN6 (`id` in schools_po / schools_vo; only ids present there). Short keys, `null` = suppressed or unknown. Data years are in each file's `years` block. None of these files is fetched until the user opens a school.

Suppression rules used everywhere: DUO `<5`, `-1` and `NA` become null. DUO totals (TOTAAL columns) and DUO's own SLAAGPERC column are never used, so a suppressed cell can not be recovered by subtraction (SLAAGPERC does leak: it can show 60 % next to a suppressed GESLAAGDEN). Cells holding 1 to 4 in the older DUO files (published unsuppressed up to 2021-2022) are treated as suppressed so all years follow the current rule. Sums over exact cells are lower bounds when any cell was suppressed and are flagged.

### detail_po.json
| Key | Meaning |
|---|---|
| `years` | `pupils` [2021..2025] (peildatum 1 Oct of that year), `eindscore` "2025-2026", `dist` "2025-2026", `advice` peildatum years of the advice history, `refniveau` "2025-2026", `heroverweging` "2025-2026" |
| `pt` | `[[year, n|null, lb]]` pupils (sum of the exact LEERJAAR_1..8 cells over M and V rows); lb=1 lower bound |
| `es` | `[[test, avg, n]]` doorstroomtoets average (latest year), one entry per test with n >= 5; tests: Route 8, IEP, DIA, AMN, DOE, LIB. Scores of different tests are not comparable. Omitted when none |
| `dm` | `[mean m, median m|null, n]` average home-to-school distance (n >= 5). The DUO median is 0 for 43 % of schools next to a large mean, which is implausible; median is null in that case |
| `lj` | `[8 numbers]` pupils per leerjaar 1-8, 2025-2026 (peildatum 1 Oct 2025). `null` per cell = suppressed (1-4 pupils) |
| `rn` | `{"lezen":[p1F,p2F,n],"taal":[p1F,p2F,n],"rekenen":[p1F,p1S,n]}` referentieniveaus of the doorstroomtoets, 2025-2026. Percent of the `n` tested pupils who reached at least 1F and 2F (lezen = DUO LV, taal = DUO TV, i.e. taalverzorging) or at least 1F and 1S (rekenen). DUO publishes mutually exclusive counts (below 1F, 1F, 2F or 1S); we add the upper categories. A subject is omitted when a needed cell is `<5`; the whole key is omitted when the school total is `<5` (so `n >= 5` always holds). Rows whose categories do not add up to the total are dropped. Small n: show a warning below about 20 |
| `hv` | `[n_reconsidered, n_raised, n_leavers]` heroverwegingen 2025-2026. `n_reconsidered` = DUO HEROVERWEGING_TOTAAL (leavers whose doorstroomtoets pointed above the advice, so the school had to reconsider), `n_raised` = BIJSTELLING (advices raised), `n_leavers` = TOTAAL (>= 5 or the key is absent). Either of the first two is null when `<5`. In 20 % of schools `n_raised` exceeds `n_reconsidered` (DUO counts adjustments outside the reconsideration group too), so do not show a ratio of the two |
| `at` | `[[year, n, s, [12 shares]]]` advice mix, same encoding as `adv` in schools_po (n = exact leavers, s = suppressed cells, shares in `levels` order, null = suppressed). `year` = peildatum year of the DUO file (2024 = the 2024-2025 file, i.e. advice given in spring 2025). The 12th level ADVIES_NIET_MOGELIJK is absent from the DUO xlsx years, so its share is null there and not counted in s |

Sources: DUO leerlingen per referentieniveau taal en rekenen 2025-2026 (xlsx), DUO heroverwegingen en bijgestelde adviezen 2025-2026 (xlsx), DUO bo-sbo leerlingen per vestiging 2021-2022 to 2025-2026 (CSV), schooladviezen 2021-2022 to 2025-2026 (CSV and xlsx), gemiddelde scores doorstroomtoets 2025-2026 (xlsx; DUO publishes it only as xlsx), gemiddelde afstand woonadres-school 2025-2026.

### detail_vo.json
| Key | Meaning |
|---|---|
| `years` | `pupils` [2021..2025], `exams` [2021..2025] (exam year = end of the school year: 2024-2025 is 2025), `catchment` 2025, `ce` [2021..2025], `zb` "2024-2025 to 2025-2026", `ov` text |
| `pt` | `[[year, n|null, lb]]` all pupils except VAVO-outsourced rows |
| `tp` | pupils by track, latest year; null = only suppressed cells; tracks with no pupils omitted. `tpl` (extra key) lists tracks whose number is a lower bound |
| `pr` | `{track: [[year, candidates, pass %, (1)]]}` pass % = geslaagden / kandidaten summed over sector/afdeling rows whose cells are both exact; null/null when fewer than 5 known candidates; a trailing 1 means some rows of that track were suppressed, so the figure covers the unsuppressed rows only. No pass rate exists for PRO or BRUGJAAR |
| `ce` | `{track: [[year, mean CE grade, candidates, (1)]]}` mean central-exam (centraal examen) grade per track and exam year 2021-2025, tracks as in `pr`. It is the candidate-weighted mean of the DUO row means (DUO "GEMIDDELD CIJFER CENTRAAL EXAMEN" per sector/afdeling), over rows with at least 5 exact candidates and a published mean; rows with `<5` candidates are left out. A trailing 1 = some rows of that track were left out, so the mean covers the disclosed rows only. Omitted when fewer than 5 candidates remain. A weighted mean of row means is an approximation of the school's true mean; show it as "about". Per-year files from DUO "geslaagden, gezakten en cijfers" |
| `zb` | `[pupils, afstromers, zittenblijvers, opstromers]` VO repeaters and down/up-streamers, school year 2024/25 to 2025/26, per vestiging (all tracks together). null per cell = `<5`; the key is absent when pupils is `<5`. Source: DUO "zittenblijvers, op- en afstroom" |
| `ov` | `{track: [ob, bb, ce, verdict]}` Inspectie onderwijsresultaten VO 2026 (CC0), 3-year averages 2022/23 to 2024/25: `ob` = onderbouwsnelheid (% of pupils moving through the onderbouw on time), `bb` = bovenbouwsucces (%), `ce` = mean central-exam grade. Each is `[value, norm after correction, 1 above norm / 0 below norm]` or null when the Inspectie did not compute it (too few pupils). `verdict` = the Inspectie's calculated verdict for the onderwijssoort ("voldoende", "onvoldoende", "onvoldoende, tenzij"; null = "geen oordeel"). This is a model output, not an Inspectie judgement of the school; norms depend on the pupil population (corrected values). Tracks: VMBO-B, VMBO-K, VMBO-GL/TL, HAVO, VWO |
| `op` | `[value, norm, 1 above / 0 below]` onderwijspositie t.o.v. advies po (per vestiging; Inspectie 2026, 3 years 2023/24 to 2025/26): net share of pupils placed above the primary advice minus below it, in percent points, so negative is common; compare to the norm only (technical note: onderwijsresultaten VO 2026 section 4.2) |
| `cm` | top 10 pupil home PC4s `[pc4, pupils, (1)]` (only PC4s with >= 5 pupils; trailing 1 = lower bound because some leerjaar cells were suppressed), `cmo` = % of known pupils living outside those 10 |

Track mapping (DUO `ONDERWIJSTYPE VO EN LEER- OF VERBLIJFSJAAR` pupils file):

| Output label | DUO value(s) |
|---|---|
| VMBO-B | VMBO BL lj 3-4 |
| VMBO-K | VMBO KL lj 3-4 |
| VMBO-GL/TL | VMBO GL lj 3-4 + VMBO TL lj 3-4 |
| HAVO | HAVO lj 4-5 |
| VWO | VWO lj 4-6 |
| PRO | Praktijkonderwijs alle vj |
| BRUGJAAR | Brugjaar 1-2 + HAVO/VWO lj 3 |

Not mapped (counted in `pt` only): Engelse Stroom, European Secondary School, Int. Baccelaureaat; `... uitbest. aan VAVO` rows are excluded everywhere. Exam file (`examenkandidaten-en-geslaagden-2020-2025`): ONDERWIJSTYPE HAVO/VWO map directly; VMBO is mapped from OPLEIDINGSNAAM: `VMBO B` to VMBO-B, `VMBO K` to VMBO-K, `VMBO G` and `VMBO T` to VMBO-GL/TL. `VMBO LWT` rows (about 500 candidates a year nationally, overlap with B/K is unclear) are left out. Sources: DUO leerlingen vo per vestiging naar onderwijstype 2021 to 2025, examenkandidaten en geslaagden 2020-2021 to 2024-2025, leerlingen per vestiging naar postcode en leerjaar 2025.

### inspection.json
Envelope: `{v:2, as_of, source, source_url, notes_url, licence, note, deeplink, deeplink_note, counts, scale, labels, labels_wv, labels_2017, labels_note, generated, schools}`. Source: Inspectie van het Onderwijs open data oordelen (po/so/vo ODS, peildatum 1 November 2026, licence CC0 1.0 per the page metadata); column notes: Inspectie "Toelichting open data oordelen en standaarden 2025/2026" (`notes_url`). One ODS row is an object van toezicht (PO cluster, SO onderwijskundige eenheid, VO onderwijssoort); `BetrokkenVestigingen` maps it to BRIN6 locations. Covers PO, SBO, SO/VSO and VO ids. 8415 of 8618 locations are listed.

**Changed in v2:** schools with "Geen eindoordeel" or "Basistoezicht" are now listed, with `o` set to that text. The front-end must test `o` against the five ratings (Goed, Voldoende, Onvoldoende, Zwak, Zeer zwak) instead of testing presence. "Geen eindoordeel" is NOT a rating (new or merged school, judgement older than four years, or the school was not visited) and is not a bad sign. Keep the old caveat: the rated set skews to schools visited after concerns; do not rank or average.

Per school `schools[BRIN6]`:

| Key | Meaning |
|---|---|
| `o` | Overall judgement. Rated: Goed / Voldoende / Onvoldoende / Zwak / Zeer zwak (VO: the worst of the rated opleidingen). Not rated: `"Geen eindoordeel"` (5876 schools, only `b`) or `"Basistoezicht"` (6) |
| `d` | Latest Vaststellingsdatum of the rated rows, YYYY-MM-DD (rated only) |
| `x` | VO, more than one rated opleiding: `{opleiding: judgement}` |
| `st` | `{standard code: judgement string}` for the school-level row (PO and SO: the single OVT row; VO: the standards that all rated opleidingen share). Keys are exactly the ODS columns, only non-empty ones. Codes that occur: OP0..OP6, VS1, VS2, OR1, OR2, SKA1..SKA3, WV1, WV2. Judgement strings: Goed, Voldoende, Onvoldoende, Voldoet, Voldoet niet, N.t.b., Niet beoordeeld, Niet te beoordelen, Hersteld binnen onderzoek (see `scale`) |
| `xs` | VO when the rated opleidingen have different standards: `{opleiding: {code: judgement}}` (instead of `st`) |
| `t`, `tc` | TypeOnderzoek text and TypeOnderzoekCode of the most recent rated row |
| `on` | Onderzoeksnummer (string) |
| `vd`, `pd` | Vaststellingsdatum and Publicatiedatum, YYYY-MM-DD |
| `k` | Kader, the framework version (e.g. `PO2021_V25`). The meaning of OP4..OP6 and WV codes depends on it |
| `b` | `[Bestuursnummer, Bestuursnaam]`, present for almost every listed school, also unrated ones |

`t`, `tc`, `on`, `vd`, `pd`, `k` describe the most recently determined rated row (for VO with several opleidingen the other opleidingen can have an older investigation). Top-level helpers:

- `counts` = `{rated, geen_eindoordeel, basistoezicht, listed, by_o:{judgement: n}}`: 2533 rated, 5876 Geen eindoordeel, 6 Basistoezicht.
- `labels` = `{code: {nl, en}}` for the codes in the file. The Dutch names are copied from the Inspectie data notes (kaders PO2021, SO2021, VO2021 and their _V23 revisions); the newer _V25/_V26 revisions and the BTL/CN kaders are not in those notes and are assumed to use the same names (`labels_note`). The English text is our short gloss. OP5 only occurs in SO and VO praktijkonderwijs, OR2 only in PO and SO. Verified against the notes: OP0 Basisvaardigheden, OP1 Aanbod, OP2 Zicht op ontwikkeling en begeleiding, OP3 Pedagogisch-didactisch handelen, OP4 Onderwijstijd, OP5 Praktijkvorming/Stage, OP6 Afsluiting, VS1 Veiligheid, VS2 Schoolklimaat, OR1 Resultaten, OR2 Sociale en maatschappelijke competenties, SKA1 Visie, ambities en doelen, SKA2 Uitvoering en kwaliteitscultuur, SKA3 Evaluatie, verantwoording en dialoog. Not verified (the owner's draft list used the 2017 meanings): OP4 "(Extra) ondersteuning" and OP6 "Samenwerking" are 2017 names; in the 2021 kader they are Onderwijstijd and Afsluiting.
- `labels_wv` = names of WV1/WV2, keyed by kader (VO_WV2021, V0_WV2023; the kader code is spelled with a zero in the data). `labels_2017` = codes of the 2017 framework (SK1 Veiligheid, SK2 Pedagogisch klimaat, OR3 Vervolgsucces, KA1..KA3, OP8 Toetsing en afsluiting ...) for older reports; none of them occurs in this file, so do not use them with the current `st`. The columns OP, SK, OR, KA, OP7, OP8, SK1, SK2, OR3, KA1..KA3, BA2, WV3..WV7 and the 1.1..6.1 series are empty in the PO/SO/VO file.
- `scale` = English gloss per judgement string. "N.t.b." is not defined in the Inspectie notes.

Deep link to the Inspectie results site (`deeplink`): `https://toezichtresultaten.onderwijsinspectie.nl/extern?code=<BRIN4>&sector=<PO|SO|VO>`, where BRIN4 is the first four characters of the school id and sector follows the schools file (PO for schools_po incl. SBO, SO for schools_so, VO for schools_vo). It is the site's own external-link route and opens the result list for that BRIN, so a VO school group shows all its locations. Checked with a headless browser for 00AR (PO, one result), 00AH (VO, 8 results) and 06SV (SO, 3 results). `/zoek?q=<BRIN4>` gives the same list; `q=<BRIN6>` returns nothing. A per-school page or a report PDF has no stable URL without the site's internal API, which we do not use (the page metadata says CC0 1.0, but the API states no licence of its own, and the owner asked not to scrape it).

The DUO copy (oordelen-v02) is a 2018 snapshot and is not used. The file is monthly: update the URL in `15_download_detail.py` and `AS_OF`/`PAGE` in `18_build_inspection.py` when refreshing.
