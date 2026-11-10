# Translations

All text a visitor can read lives in `site/i18n/<code>.json`. The page loads `en.json` first (it is the fallback), then the chosen language on top of it. A missing key falls back to English and logs one `console.warn` per key.

## Add a language

1. Copy `en.json` to `<code>.json`, for example `nl.json` (use the plain language code: `nl`, `de`, `ar`).
2. Translate the **values**. Never change a key.
3. In `site/app.js`, add the code to `SUPPORTED` and a line to `LANG_META` (native name, and the locale used for numbers and dates, for example `nl: {name:'Nederlands', locale:'nl-NL'}`). Right-to-left codes (`ar`, `he`, `fa`, `ur`) are listed in `RTL_LANGS`, and `<html dir>` follows automatically.
4. The language switcher in the masthead appears by itself as soon as `SUPPORTED` has more than one code. The deploy workflow copies every `site/i18n/*.json`, so nothing else to do.

Language is picked from `?lang=xx`, then the saved choice (`localStorage`), then the browser language list, then `en`. Changing language re-renders in place and keeps the route.

## Key conventions

- Dotted paths, grouped by screen or feature: `nav.*`, `form.*`, `route.*`, `stops.<id>.*`, `panel.*`, `filters.*`, `find.*`, `map.*`, `cmp.*`, `prof.*` (school profile), `sys.*` (system diagram), `faq.*`, `sources.*`, `foot.*`.
- `{name}` is replaced by a value. `{brand}` is always available and is `brand.name`. Keep every placeholder in the translation.
- Plurals are an object: `{"one": "{n} school", "other": "{n} schools"}`. Add the other CLDR categories your language needs (`few`, `many`, `zero`, `two`).
- Arrays and objects hold structured content (glossary pairs, stop paragraphs, FAQ blocks, system-diagram transfer list). Keep the same shape and the same number of items.
- The only markup allowed inside a string is `<b>...</b>` and only where the English string already uses it. Everything else is plain text.
- Keep the no-dash house style: no en dashes or em dashes in prose, rewrite the sentence instead.
- The site name and tagline are `brand.name` and `brand.tagline`. Renaming the site is a one-line change there.

## What must not be translated

- Data values from the pipeline JSON: school names, places, municipality names, BRIN ids, DUO structure labels, inspection judgements and the attribution and disclaimer text inside `meta.json`.
- Dutch official terms. Keep them as terms inside the translated sentence and explain them, as the English strings do: groep, schooladvies, doorstroomtoets, brugklas, vmbo (basis, kader, gl/tl), havo, vwo, mbo, hbo, wo, praktijkonderwijs, tto, ISK, sbo, propedeuse, Montessori, Dalton, Jenaplan, vrije school, and the names of institutions (DUO, Inspectie van het Onderwijs, Nuffic, Rijksoverheid, Scholen op de kaart).
- Dutch denomination keys under `den` are the lookup keys (left side), only the values are translated.
- Source titles (`src.*`) may be translated, the links they point to are not.
- Map tiles and the Leaflet zoom buttons are not covered by these files.
