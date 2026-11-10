# Dutch School Path (dutch-school-finder)

Dutch schools explained in English, for families new to the Netherlands. Enter your child's age and a
postcode and you get the steps still ahead (with dates and what to do) and the real schools near you
that fit each step: pupil numbers, the school advice its leavers received, exam results, school
concepts (Montessori, Dalton, bilingual, IB and more) and upcoming open days.

Everything runs in the browser from precomputed open data. Nothing you enter is sent anywhere.

## Layout

| Path | What |
|---|---|
| `site/index.html` | the page shell (header, tabs, footer, one section per view). `build/prerender.py` turns it into every real page |
| `site/app.js`, `site/app.css`, `site/i18n/` | the app, its styles and all text |
| `site/seo.json` | site URL, base path, `indexable` switch, language list |
| `site/og.png`, `site/favicon.svg` | social image (1200 x 630) and icon; `favicon.ico` is generated at build time |
| `build/prerender.py` | writes `_site/`: static HTML for every page, sitemaps, `robots.txt`, `404.html`, copied assets and `data/` |
| `build/check_site.py` | link, id, heading, head-tag, JSON-LD and sitemap checker for a built `_site/` |
| `pipeline/` | open-data pipeline that builds `pipeline/out/*.json` (see `pipeline/README.md`) |
| `.github/workflows/pages.yml` | runs `python -I build/prerender.py` and deploys `_site/` to GitHub Pages |

## URLs

Real paths under `base_path` (History API in the browser, one prerendered `index.html` per path, no CMS):

| Path | Page |
|---|---|
| `/` | start page (route finder); `/?pc=1011` pre-fills a postcode |
| `/find/`, `/map/` | search and map; filters live in the query string |
| `/system/`, `/questions/`, `/sources/` | whole system, FAQ (`/questions/#<slug>` per question), data and sources |
| `/school/<brin6>-<name>-<city>/` | one page per school location (8,600+); a bare `/school/<brin6>/` is resolved client-side by `404.html` |
| `/municipality/<slug>/`, `/municipalities/` | schools per municipality, A to Z index by province |
| `/compare/?ids=A,B` | client-side comparison, always `noindex`, not in the sitemap |

Old hash links (`#/school/ID`, `#/faq?q=slug`, `#/compare/A,B`, `#/find?...`) are rewritten to these paths
when the page opens. Slugs are built by the same rule in `build/prerender.py` and `site/app.js` (`slugify`).

## Build and run locally

```
python -I build/prerender.py        # writes _site/ (about 15 s)
python -I build/check_site.py       # optional, about 3 minutes: links, ids, headings, JSON-LD, sitemaps
```

`_site/` is git-ignored. It must be served under `base_path` (default `/dutch-school-finder/`): serve the
parent folder of a copy named `dutch-school-finder`, or set `"base_path": "/"` in a temporary copy of
`seo.json` and build with `python -I build/prerender.py --seo my-seo.json --out _local`, then
`python -m http.server -d _local`. GitHub Pages serves `404.html` for unknown paths; a plain `http.server` does not.

## Search engines: the `indexable` switch

`site/seo.json` has one switch, `indexable`.

- `false` (now): every page carries `<meta name="robots" content="noindex, nofollow">`. `robots.txt` still
  allows crawling (so bots can read the noindex) and has no `Sitemap:` line.
- `true`: pages carry `index, follow` (`compare/` and `404.html` stay `noindex, follow`) and `robots.txt`
  lists `Sitemap: <site_url>/sitemap.xml`.

Nothing else changes. The sitemaps (`sitemap.xml` index, `sitemap-pages.xml`, `sitemap-schools.xml`,
`sitemap-municipalities.xml`) are always generated. Note that crawlers only read `robots.txt` at the root of a
host, so on the project URL (`...github.io/dutch-school-finder/`) it has no effect; it works on a custom domain.

## Going live on a custom domain

1. Edit `site/seo.json`: set `site_url` to the new origin (no trailing slash, e.g. `https://dutchschoolpath.example`)
   and `base_path` to `/`. Nothing else in the code refers to the old address.
2. Add a file named `CNAME` that contains just the domain to `site/` (the build copies it into `_site/`), and set the
   same domain under Settings, Pages, Custom domain. Point the domain's DNS at GitHub Pages and tick "Enforce HTTPS".
3. Flip `"indexable": true` in `site/seo.json`, commit and let the workflow deploy.
4. Open Google Search Console, add the domain property, and submit `https://<domain>/sitemap.xml`.
   Check one school page with the URL inspection tool.

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
