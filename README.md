# Schoollijn (Dutch School Finder)

Dutch schools explained in English, for families new to the Netherlands. Enter your child's age and a
postcode and you get the steps still ahead (with dates and what to do) and the real schools near you
that fit each step: pupil numbers, the school advice its leavers received, exam results, school
concepts (Montessori, Dalton, bilingual, IB and more) and upcoming open days.

Everything runs in the browser from precomputed open data. Nothing you enter is sent anywhere.

## Layout

| Path | What |
|---|---|
| `site/index.html` | the whole site: one static page |
| `pipeline/` | open-data pipeline that builds `pipeline/out/*.json` (see `pipeline/README.md`) |
| `.github/workflows/pages.yml` | deploys `site/` plus `pipeline/out/` as `data/` to GitHub Pages |

Run locally: copy `pipeline/out/*.json` into `site/data/` (or serve the assembled `_site/`) and open it
through any static server, e.g. `python -m http.server`.

## Data and licences

- School addresses, pupil numbers, school advice and exam results: DUO Open Onderwijsdata, CC BY 4.0.
- Postcode areas: CBS Postcode4 via PDOK, CC BY 4.0.
- Address coordinates and municipalities: Kadaster BAG via PDOK Locatieserver.
- School concepts and open days: published association lists and the schools' own websites, with the
  source and check date shown per item.

Not affiliated with DUO, CBS, Kadaster, PDOK or Scholen op de kaart. No data from Scholen op de kaart is
used; the site only links to its search.

Code: MIT licence. Author: Ernst van Gassen, Arktos AI Lab.

The 2025 prototype (FastAPI + React) is kept on the `archive-2025` branch.
