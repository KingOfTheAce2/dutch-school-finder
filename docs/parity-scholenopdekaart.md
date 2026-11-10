# Feature parity with Scholen op de kaart (SodK)

Status 2026-11-10. Purpose: list what a school page on scholenopdekaart.nl shows, what we already show, and which open source could close each gap.

Method and limits. I viewed three public school pages (the primary school "De Maasparel" in Stevensweert, the secondary school Vossius Gymnasium in Amsterdam, the special-education school De Aventurijn in Assen) and their sub-pages (Het onderwijs, Resultaten, Tevredenheid) only to list section names and metric labels. No SodK data, text, document or number is stored or reused anywhere in this repo, and nothing was fetched at scale. The inventory below is a feature list in our own words. Where SodK labels a source at all it says only "Bron" (and, for the inspection block, the Inspectie); a large part of every page is text written by the school.

Legend for "Do we have it": yes = in `pipeline/out` now, partial = some of it, no = not shown.

## Parity table

| # | SodK feature | Do we have it | Open data source that could power it | Plan |
|---|---|---|---|---|
| 1 | School self-description: introduction, mission and vision, school characteristics | no | Not open (school-supplied, e.g. Vensters profile) | Out of scope. Link to the school website (`web`) instead. |
| 2 | Type of education, denomination, size class | yes | DUO address files | Done (`den`, `sbo`, `so_type`, `cl`). |
| 3 | Pupil count, 3-year trend, national average | partial | DUO leerlingen per vestiging (have trend `pt`) | National/province average can be computed from our own files; add in the front-end. |
| 4 | Pupils per leerjaar (PO) | yes | DUO leerlingen bo/sbo leerjaar geslacht 2025-2026 | Done: `lj` in detail_po. |
| 5 | Pupils per age or per verblijfsjaar (PO, SO, VSO) | no | DUO "leerlingen po naar soort po, cluster en leeftijd" (`raw/so_leerlingen_2025-2026.csv`, age columns, already downloaded) | Cheap: add an `ages` array for schools_so and detail_po. https://duo.nl/open_onderwijsdata/primair-onderwijs/aantal-leerlingen/leerlingen-onderwijssoort-cluster-leeftijd.jsp |
| 6 | VO pupils by onderwijssoort and leerjaar table | partial | DUO leerlingen VO per vestiging naar onderwijstype (have totals per track `tp`) | Cheap: keep the leerjaar cells per track. |
| 7 | Where pupils live (postcode area, count, percent) | partial | VO: DUO leerlingen per vestiging naar postcode en leerjaar (have `cm`). PO: DUO publishes pupils per municipality and postcode, not per school, as far as the dataset title shows | VO done. PO: check the DUO "leerlingen per gemeente, postcode en leeftijd" file for a school key; otherwise not possible. |
| 8 | School hours, childcare (voor/na/tussen schooltijd), holiday dates | no | Not open per school. Holiday regions are national (Rijksoverheid); DUO address file has VAKANTIEREGIO | Show the national holiday calendar per region (open, tiny). School hours: not open. |
| 9 | Practical info: parent involvement, complaints procedure, admission policy, sick leave, leave | no | Not open (school-supplied) | Out of scope. Explain the generic Dutch rules in the guide (already partly there). |
| 10 | Ouderbijdrage amount and voluntariness | partial | Amount is school-supplied, not open. Inspectie standard WV1 "vrijwillige ouderbijdrage" for the few VO schools inspected on it | We show WV1 in `st` where present (22 + 57 rows). The amount stays unavailable. |
| 11 | Social safety: protocols, monitor, anti-bullying coordinator | partial | Documents are school-supplied. Inspectie standard VS1 Veiligheid and VS2 Schoolklimaat are open | Now in `inspection.st`. Suspension data: Inspectie "schorsingen en verwijderingen" (CC0, per object van toezicht), not built. |
| 12 | Staff: gender, age, function groups, specialists | no | DUO personeel PO/VO open data (institution or board level, not per vestiging). https://duo.nl/open_onderwijsdata/primair-onderwijs/personeel/index.jsp | Medium effort, institution level only (BRIN4). Worth a spike; flag as "school group level". |
| 13 | Time spent per subject / onderwijstijd | no | Not open (school-supplied) | Out of scope. |
| 14 | Class grouping, facilities, remedial specialists, early-years offer, vakleerkrachten, school plan, support profile | no | Not open (school-supplied PDFs and text) | Out of scope. |
| 15 | Doorstroomtoets: share reaching fundamental and target level | yes | DUO leerlingen per referentieniveau taal en rekenen | Done: `rn`. The Inspectie file "leerresultaten primair onderwijs" (CC0, per school, with signaleringswaarde and 3-year pooling) could add the pass/fail-against-norm flag. |
| 16 | Interim test results (tussentijdse toetsen) | no | Not open | Out of scope. |
| 17 | School advice with comparison to similar schools | partial | DUO schooladviezen (have 5 years `at`) | Comparison group: build national and same-province averages from our own data; "vergelijkbare scholen" is SodK's own grouping and not reproduced. |
| 18 | Social development methods and values | no | Not open | Out of scope. |
| 19 | What the Inspectie says (judgement and per-standard scores, link) | yes | Inspectie open data oordelen (CC0), toezichtresultaten deep link | Done: `inspection.json` v2 (`o`, `st`, `xs`, `labels`, `deeplink`). |
| 20 | VO: placement in year 3 against the primary advice | yes | Inspectie onderwijsresultaten VO 2026 (CC0) | Done: `op` in detail_vo. |
| 21 | VO: progression in onderbouw and bovenbouw | yes | Same Inspectie file; DUO zittenblijvers, op- en afstroom | Done: `ov` (onderbouwsnelheid, bovenbouwsucces), `zb`. |
| 22 | Pass rate per exam year and trend | yes | DUO examenkandidaten en geslaagden | Done per track (`pr`). |
| 23 | Pass rate per profile | no | DUO exam files have one row per afdeling/profile (already in `raw/`) | Cheap: expose per-profile rows for HAVO/VWO. |
| 24 | Exam grades: SE, CE, final grade, with comparison | partial | DUO geslaagden, gezakten en cijfers (has SE, CE and cijferlijst) | `ce` done. Add SE and cijferlijst means with the same weighting; per-subject grades exist in DUO "examenkandidaten en examencijfers" per level (large files). |
| 25 | VO profile choice table (vwo profiles over years) | no | Probably DUO leerlingen VO naar onderwijstype (programme/profile rows); not verified | Check the 2023 to 2025 files for profile rows before promising it. |
| 26 | Pupil satisfaction (overall score, per question, national average, 3-year trend) | no | Not open (school-supplied survey results published through Vensters) | Cannot be done. Say so in the methods page. |
| 27 | Parent and staff satisfaction | no | Not open | Cannot be done. |
| 28 | Atmosphere and safety survey scores | no | Not open per school | Cannot be done. Inspectie VS1/VS2 is the open substitute. |
| 29 | Open day and open evening | partial | features.json `open_days` from school websites (our own crawl, not an open dataset) | Keep, label as "from the school's website". |
| 30 | SO/VSO: cluster, school type | yes | DUO address file (CLUSTER, ONDERWIJS) | Done: `schools_so.json` (`so_type`, `cl`, `cls`). |
| 31 | SO/VSO: pupils per age or verblijfsjaar | no | Same DUO age file as #5 | Cheap, see #5. |
| 32 | SO/VSO: samenwerkingsverband and partner organisations | no | SWV code is in DUO files (`SWV_VESTIGING`) and DUO publishes "scholen per samenwerkingsverband"; partners are school-supplied | Medium: add SWV name per school. Partner lists stay unavailable. |
| 33 | SO/VSO: support profile, admission criteria (TLV), destination of leavers per school | no | VSO uitstroom is open only per samenwerkingsverband (`raw/vso_uitstroom_2025-2026.csv`); the rest is school-supplied | Show uitstroom at SWV level only if the SWV key is added (#32). |
| 34 | Contact: address, website, map | yes | DUO, PDOK | Done. |
| 35 | Contact: telephone, board name and board size | partial | DUO address files carry TELEFOONNUMMER and BEVOEGD GEZAG; board name from Inspectie (`b`); board totals computable | Cheap: add `tel` and board totals. Decide whether to publish phone numbers. |
| 36 | "Landelijk gemiddelde" and "vergelijkbare scholen" comparisons | partial | Computable from our files (national and province level) | Compute offline into meta or in the front-end; no new source. |
| 37 | School guide and school plan downloads | no | Not open (school documents) | Out of scope; link to the school site. |
| 38 | Waiting list, phone-free, other school-set flags | no | Not open | Out of scope. |

Counts: 9 yes, 10 partial, 19 no (38 rows). Of the 19 "no", 13 are school-supplied or survey content that no open source covers (#1, #8, #9, #13, #14, #16, #18, #26, #27, #28, #33, #37, #38). The other 6 have an open source: #5, #23 and #31 are cheap (data already in `raw/`), #12, #25 and #32 need a spike.

## Top gaps that remain, and why

1. Satisfaction and safety surveys (#26 to #28). Collected by schools through Vensters; not published as open data per school.
2. School self-description and practical information (#1, #8, #9, #13, #14, #37, #38) including schooltijden, opvang and the ouderbijdrage amount (#10). School-supplied text.
3. Staff profile (#12). Open at institution level in DUO personeel, not per vestiging, and not built.
4. Special-education depth (#33): ondersteuningsprofiel, TLV criteria, leaver destinations per school. Only SWV-level uitstroom is open.
5. PO catchment per school and "similar schools" comparison (#7, #17, #36). The first has no per-school open file that I could find; the second is SodK's own grouping, so we offer national and province comparison instead.

## Open data found during the analysis and not built yet

All CC0 or CC BY, all per school or per vestiging, listed by value for an expat audience.

| Dataset | Source | What it would add |
|---|---|---|
| Leerresultaten primair onderwijs 2024, 2025, 2026 | Inspectie, CC0 (https://www.onderwijsinspectie.nl/trends-en-ontwikkelingen/onderwijsdata/leerresultaten-primair-onderwijs) | Per school 3-year referentieniveaus with the Inspectie signaleringswaarde |
| Schorsingen en verwijderingen | Inspectie, CC0 (https://www.onderwijsinspectie.nl/trends-en-ontwikkelingen/onderwijsdata/schorsingen-en-verwijderingen) | Counts per object van toezicht |
| Excellente scholen | Inspectie, CC0 | Names and places of schools with the predicaat |
| Schoolweging PO | Inspectie/CBS, CC0 | Pupil population indicator per school (context for results) |
| DUO personeel | DUO | Staff composition at institution level |
| DUO exam files (SE, cijferlijst, profile rows) | DUO, already in `raw/` | Items #23 and #24 |

## What we have that SodK lacks for expats

- English throughout: guide, field explanations, the Dutch system explained, English glosses for every Inspectie standard and judgement.
- Concept and international flags that DUO does not carry: tweetalig (tto), IB, international departments, newcomer classes (ISK, schakelklas), Technasium, Montessori, Dalton, Jenaplan, vrije school, each with evidence and a confidence level (features.json).
- Search from the family's own postcode with distance (PC4 centroid), instead of by municipality name only.
- Five-year school-advice mix per school and the average home-to-school distance (`dm`), which tell an expat family how local or regional a school's intake is.
- Heroverwegingen (advice reconsiderations) per school next to the doorstroomtoets levels.
- Explicit handling of small numbers: suppressed cells stay null, lower bounds are flagged, no subtraction tricks, no ranking of inspection results.
- Special education with the four clusters explained in plain English, together with the SBO schools.
- A Data sources page with licence and attribution per source, and a documented method.
- Deep link to the Inspectie's own results page per school.
