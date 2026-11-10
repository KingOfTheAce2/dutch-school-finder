#!/usr/bin/env python3
"""Prerender Schoolpath NL into _site/: real paths, static HTML in <main> for every page.

Run from anywhere:  python -I build/prerender.py [--out DIR] [--seo FILE]

Inputs : site/index.html (shell), site/app.js + app.css + i18n/*.json + seo.json + og.png,
         pipeline/out/*.json (open data).
Output : _site/ = the deployable site (pages, sitemaps, robots.txt, 404.html, copied assets, data/).
Stdlib only. The slug rule (slugify) is the same as in site/app.js.
"""
import argparse
import hashlib
import html
import json
import math
import re
import shutil
import struct
import sys
import unicodedata
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "pipeline" / "out"

# ---------------------------------------------------------------- small helpers


def e(s):
    return html.escape(str(s), quote=True)


def jload(p):
    with open(p, encoding="utf8") as f:
        return json.load(f)


_SPECIAL = [("ß", "ss"), ("æ", "ae"), ("œ", "oe"), ("ø", "o"), ("đ", "d"), ("ð", "d"), ("ł", "l"), ("ı", "i"), ("þ", "th")]


def slugify(s):
    """Same rule as slugify() in site/app.js."""
    s = unicodedata.normalize("NFKD", "" if s is None else str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    for a, b in _SPECIAL:
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def school_slug(s):
    n = slugify(s["name"])[:60].rstrip("-")
    c = slugify(s["city"])
    return s["id"].lower() + ("-" + n if n else "") + ("-" + c if c else "")


def nf(n):
    return f"{n:,}"


def jr(x):
    """Math.round"""
    return int(math.floor(x + 0.5))


def nf1(x):
    return f"{x:,.1f}"


def num(x):
    """number the way JS prints it in an attribute"""
    if isinstance(x, float) and x == int(x):
        x = int(x)
    return str(x)


# ---------------------------------------------------------------- i18n like app.js


class Tr:
    def __init__(self, d):
        self.d = d

    def raw(self, key):
        o = self.d
        for p in key.split("."):
            if not isinstance(o, dict) or p not in o:
                raise KeyError(key)
            o = o[p]
        return o

    def has(self, key):
        try:
            self.raw(key)
            return True
        except KeyError:
            return False

    def __call__(self, key, **v):
        o = self.raw(key)
        if isinstance(o, dict):
            n = v.get("n")
            o = o["one"] if n == 1 and "one" in o else o["other"]
        if not isinstance(o, str):
            raise TypeError(key)

        def fill(m):
            k = m.group(1)
            if k in v and v[k] is not None:
                x = v[k]
                return nf(x) if isinstance(x, int) and not isinstance(x, bool) else str(x)
            if k == "brand":
                return self.d["brand"]["name"]
            return m.group(0)

        return re.sub(r"\{(\w+)\}", fill, o)


def rich(s):
    """only <b>..</b> survives, everything else is text (like rich() in app.js)"""
    parts = re.split(r"(</?b>)", str(s))
    out = []
    for p in parts:
        if p in ("<b>", "</b>"):
            out.append(p)
        else:
            out.append(e(p))
    return "".join(out)


# ---------------------------------------------------------------- constants read from app.js (single source of truth)


def read_app_consts(js):
    m = re.search(r"var SRC_URL=\{(.*?)\n\};", js, re.S)
    src_url = dict(re.findall(r"(\w+):'([^']+)'", m.group(1)))
    m = re.search(r"var SRC_ORDER=\[(.*?)\];", js, re.S)
    src_order = re.findall(r"'([^']+)'", m.group(1))
    m = re.search(r"var LAST_CHECKED='([^']+)'", js)
    last_checked = m.group(1)
    m = re.search(r"var FEAT_ATTR=\[(.*?)\];\nfunction renderFooter", js, re.S)
    feat_attr = re.findall(r"\['(\w+)','([^']+)','([^']*)'\]", m.group(1))
    assert src_url and src_order and feat_attr
    return src_url, src_order, last_checked, feat_attr


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def fmt_day(iso):
    y, mo, d = (int(x) for x in iso.split("-"))
    return f"{d} {MONTHS[mo - 1]} {y}"


# ---------------------------------------------------------------- data


def load_schools():
    out = []
    for fname, sec_of in (("schools_po", lambda r: "sbo" if r["sbo"] else "po"), ("schools_vo", lambda r: "vo"), ("schools_so", lambda r: "so")):
        j = jload(DATA / f"{fname}.json")
        cols = j["cols"]
        for row in j["rows"]:
            r = dict(zip(cols, row))
            r["sec"] = sec_of(r)
            r["denNl"] = j["den"][r["den"]] if r.get("den") is not None and r["den"] >= 0 else ""
            r["provN"] = j["prov"][r["prov"]] if r.get("prov") is not None and 0 <= r["prov"] < len(j["prov"]) else ""
            r["_levels"] = j.get("levels")
            r["_clusters"] = j.get("clusters")
            r["name"] = r["name"] or ""
            r["city"] = r["city"] or ""
            r["mun"] = r["mun"] or ""
            out.append(r)
    return out


def hav(lat1, lon1, lat2, lon2):
    la1 = lat1 * math.pi / 180
    la2 = lat2 * math.pi / 180
    dl = (la2 - la1) / 2
    dn = (lon2 - lon1) * math.pi / 360
    a = math.sin(dl) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dn) ** 2
    return 12742 * math.asin(min(1, math.sqrt(a)))


def nearest_same_type(schools, k=5):
    """id -> [(school, km)] the k nearest schools of the same sec (same rule as nearbySection in app.js)"""
    res = {}
    CELL = 0.05
    for sec in ("po", "sbo", "vo", "so"):
        grp = [s for s in schools if s["sec"] == sec and s["g"] != 3 and s["lat"] is not None]
        grid = {}
        for s in grp:
            grid.setdefault((int(s["lat"] / CELL), int(s["lon"] / CELL)), []).append(s)
        brute = len(grp) < 1200
        for s in grp:
            if brute:
                cand = [(hav(s["lat"], s["lon"], o["lat"], o["lon"]), o) for o in grp if o is not s]
                cand.sort(key=lambda x: (x[0], x[1]["id"]))
                res[s["id"]] = [(o, d) for d, o in cand[:k]]
                continue
            cy, cx = int(s["lat"] / CELL), int(s["lon"] / CELL)
            found = []
            r = 0
            while r < 400:
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if max(abs(dy), abs(dx)) != r:
                            continue
                        for o in grid.get((cy + dy, cx + dx), ()):
                            if o is not s:
                                found.append((hav(s["lat"], s["lon"], o["lat"], o["lon"]), o))
                found.sort(key=lambda x: (x[0], x[1]["id"]))
                # a cell is at least ~3.3 km wide at 53 degrees north; anything unseen is farther than r*3.3 km
                if len(found) >= k and found[k - 1][0] <= r * 3.3:
                    break
                r += 1
            res[s["id"]] = [(o, d) for d, o in found[:k]]
    return res


# ---------------------------------------------------------------- the build


class Build:
    def __init__(self, out_dir, seo_path):
        self.out = Path(out_dir)
        self.seo = jload(seo_path)
        self.site_url = self.seo["site_url"].rstrip("/")
        self.base = self.seo["base_path"]
        assert self.base.startswith("/") and self.base.endswith("/")
        self.indexable = bool(self.seo["indexable"])
        self.langs = self.seo["lang"]
        self.en = jload(SITE / "i18n" / "en.json")
        self.t = Tr(self.en)
        self.brand = self.en["brand"]["name"]
        self.js = (SITE / "app.js").read_text(encoding="utf8")
        self.src_url, self.src_order, self.last_checked, self.feat_attr = read_app_consts(self.js)
        self.shell = (SITE / "index.html").read_text(encoding="utf8")
        self.meta = jload(DATA / "meta.json")
        self.insp = jload(DATA / "inspection.json")
        self.feat = jload(DATA / "features.json")
        self.det_vo = jload(DATA / "detail_vo.json")
        self.det_po = jload(DATA / "detail_po.json")
        self.schools = load_schools()
        self.tcount = {}
        for s in self.schools:
            k = (s["name"], s["city"], s["sec"])
            self.tcount[k] = self.tcount.get(k, 0) + 1
            k = k + (s["addr"],)
            self.tcount[k] = self.tcount.get(k, 0) + 1
        self.pages = 0
        self.sitemap = {"pages": [], "schools": [], "municipalities": []}
        self.ver = {}
        for f in ("app.js", "app.css"):
            self.ver[f] = hashlib.sha1((SITE / f).read_bytes()).hexdigest()[:8]
        self.generated = max(str(self.meta.get("generated", "")), str(self.insp.get("generated", "")), str(self.det_vo.get("generated", "")))
        self.site_lastmod = max(self.generated, self.last_checked)

    # ------------------------------------------------------------ url helpers
    def href(self, rel):
        return self.base + rel

    def canon(self, rel):
        return self.site_url + "/" + rel

    def out_path(self, rel):
        return self.out / rel / "index.html" if rel else self.out / "index.html"

    # ------------------------------------------------------------ data helpers
    def data_year(self, key):
        m = (self.meta.get("data_years") or {}).get(key)
        if not m:
            return "", ""
        a = re.match(r"(\d{4}-\d{4})", m)
        d = re.search(r"(\d{4}-\d{2}-\d{2})", m)
        return (a.group(1) if a else ""), (d.group(1) if d else "")

    def den_label(self, nl):
        m = self.en["den"]
        return m.get(nl, self.en["den"]["other"])

    def feat_list(self, sid):
        f = self.feat["schools"].get(sid)
        out = []
        if not f or not isinstance(f.get("flags"), list):
            return out
        for k in ["tto", "ib", "technasium", "international", "montessori", "dalton", "jenaplan", "vrije_school", "newcomer"]:
            if k not in f["flags"]:
                continue
            c = (f.get("confidence") or {}).get(k)
            if c not in ("high", "medium"):
                continue
            out.append((k, c, (f.get("evidence") or {}).get(k)))
        return out

    def safe_url(self, u):
        return u if isinstance(u, str) and re.match(r"^https?://[^\s\"'<>]+$", u, re.I) else None

    def safe_web(self, w):
        return "https://" + w if w and re.match(r"^[a-z0-9][a-z0-9.\-/_%?=&:~#+@]*$", w, re.I) else None

    def feat_src_name(self, url, kind):
        t = self.t
        if kind != "list":
            return t("feat.src.site")
        host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", url).split("/")[0])
        for dom, key in [("nuffic.nl", "nuffic"), ("technasium.nl", "technasium"), ("montessori.nl", "montessori"), ("dalton.nl", "dalton"), ("jenaplan.nl", "jenaplan"), ("vrijescholen.nl", "vrije"), ("dutchinternationalschools.nl", "dis"), ("sio.nl", "sio"), ("duo.nl", "duo")]:
            if host.endswith(dom):
                return t("feat.src." + key)
        return t("feat.src.other")

    def feat_chips(self, sid):
        t = self.t
        lst = self.feat_list(sid)
        if not lst:
            return ""
        out = ['<div class="fts">']
        for k, c, ev in lst:
            src = self.feat_src_name(ev[0], ev[2]) if ev else t("feat.src.site")
            tip = t("feat.tip", label=t("ft." + k), src=src, checked=t("feat.checked", date=ev[3]) if ev and ev[3] else "", less=t("feat.less") if c == "medium" else "")
            cls = "ft" + (" md" if c == "medium" else "")
            url = self.safe_url(ev[0]) if ev else None
            if url:
                out.append(f'<a class="{cls}" href="{e(url)}" target="_blank" rel="noopener" title="{e(tip)}">{e(t("ft." + k))}</a>')
            else:
                out.append(f'<span class="{cls}" title="{e(tip)}">{e(t("ft." + k))}</span>')
        out.append("</div>")
        return "".join(out)

    # ------------------------------------------------------------ html shell
    def head(self, p):
        t = self.t
        rel = p.get("rel")
        title = p["title"]
        desc = p["desc"]
        robots_idx = p.get("index", True) and self.indexable
        robots = ("index, follow" if robots_idx else ("noindex, follow" if self.indexable else "noindex, nofollow"))
        h = ['<meta charset="utf-8">', '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">']
        h.append(f"<title>{e(title)}</title>")
        h.append(f'<meta name="description" content="{e(desc)}">')
        h.append(f'<meta name="robots" content="{robots}">')
        h.append(f'<meta name="theme-color" content="#FFC917">')
        h.append(f'<meta name="sp-base" content="{e(self.base)}">')
        if p.get("canonical", True):
            url = self.canon(rel)
            h.append(f'<link rel="canonical" href="{e(url)}">')
            first = self.langs[0]
            for lg in self.langs:
                u = url if lg == first else url + ("&" if "?" in url else "?") + "lang=" + lg
                h.append(f'<link rel="alternate" hreflang="{e(lg)}" href="{e(u)}">')
            h.append(f'<link rel="alternate" hreflang="x-default" href="{e(url)}">')
            h.append(f'<meta property="og:url" content="{e(url)}">')
        img = self.site_url + "/og.png"
        h.append('<meta property="og:type" content="website">')
        h.append(f'<meta property="og:site_name" content="{e(self.brand)}">')
        h.append(f'<meta property="og:title" content="{e(title)}">')
        h.append(f'<meta property="og:description" content="{e(desc)}">')
        h.append(f'<meta property="og:locale" content="en_GB">')
        h.append(f'<meta property="og:image" content="{e(img)}">')
        h.append('<meta property="og:image:width" content="1200">')
        h.append('<meta property="og:image:height" content="630">')
        h.append(f'<meta property="og:image:alt" content="{e(self.brand)}: {e(self.en["brand"]["tagline"])}">')
        h.append('<meta name="twitter:card" content="summary_large_image">')
        h.append(f'<meta name="twitter:title" content="{e(title)}">')
        h.append(f'<meta name="twitter:description" content="{e(desc)}">')
        h.append(f'<meta name="twitter:image" content="{e(img)}">')
        h.append(f'<link rel="icon" type="image/svg+xml" href="{self.base}favicon.svg">')
        h.append(f'<link rel="icon" type="image/x-icon" sizes="32x32" href="{self.base}favicon.ico">')
        h.append('<link rel="preconnect" href="https://fonts.googleapis.com">')
        h.append('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>')
        h.append('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@500;700;800;900&family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&display=swap">')
        h.append(f'<link rel="stylesheet" href="{self.base}app.css?v={self.ver["app.css"]}">')
        for ld in p.get("jsonld", []):
            h.append('<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>")
        return "\n".join(h)

    def fill_i18n(self, s):
        t = self.t

        def el(m):
            tag, attrs, key = m.group(1), m.group(2), m.group(3)
            return f"<{tag}{attrs}>{e(t(key))}</{tag}>"

        s = re.sub(r'<(\w+)([^<>]*\bdata-i18n="([^"]+)"[^<>]*)></\1>', el, s)

        def at(m):
            tag, attrs, spec = m.group(1), m.group(2), m.group(3)
            extra = ""
            for pair in spec.split(";"):
                k, _, v = pair.partition(":")
                extra += f' {k.strip()}="{e(t(v.strip()))}"'
            return f"<{tag}{extra}{attrs}>"

        s = re.sub(r'<(\w+)([^<>]*\bdata-i18n-attr="([^"]+)"[^<>]*)>', at, s)

        route_rel = {"route": "", "find": "find/", "map": "map/", "system": "system/", "faq": "questions/", "sources": "sources/"}

        def rt(m):
            tag, attrs, name = m.group(1), m.group(2), m.group(3)
            return f'<{tag} href="{self.href(route_rel[name])}"{attrs}>'

        s = re.sub(r'<(a)([^<>]*\bdata-route="(\w+)"[^<>]*)>', rt, s)
        return s

    def page(self, p):
        """p: rel, view, title, desc, slots (dict), jsonld, index, tab, schoolid"""
        t = self.t
        view = p["view"]
        s = self.shell
        s = s.replace("<!--@head-->", self.head(p))
        s = s.replace("<!--@bodyattrs-->", f' data-view="{view}"')
        s = s.replace("<!--@appjs-->", f'{self.base}app.js?v={self.ver["app.js"]}')
        # hidden sections; the active one carries the h1
        for v in ("route", "find", "map", "school", "compare", "system", "faq", "sources", "static"):
            s = s.replace(f"<!--@hide:{v}-->", "" if v == view else " hidden")
        if view not in ("route", "school", "static"):
            m = re.search(rf'<section id="p-{view}".*?</section>', s, re.S)
            blk = m.group(0)
            nb = blk.replace('<h2 class="vh"', '<h1 class="vh"', 1)
            nb = nb.replace("</h2>", "</h1>", 1)
            assert nb != blk
            s = s.replace(blk, nb)
        # hero title: h1 on the start page, a plain paragraph elsewhere
        hero = e(t("hero.title"))
        s = s.replace("<!--@h1-->", f'<h1 id="h1" class="h1" data-i18n="hero.title">{hero}</h1>' if view == "route" else '<p id="h1" class="h1" data-i18n="hero.title"></p>')
        # text is filled in only where it is visible; hidden sections and the hero (off the start page) are left to app.js
        stash = []

        def keep(m):
            stash.append(m.group(0))
            return f"@@{len(stash) - 1}@@"

        s = re.sub(r'<section id="p-\w+" hidden>.*?</section>', keep, s, flags=re.S)
        if view != "route":
            s = re.sub(r'<section class="hero".*?</section>', keep, s, flags=re.S)
        s = self.fill_i18n(s)
        s = re.sub(r"@@(\d+)@@", lambda m: stash[int(m.group(1))], s)
        # current tab
        tab = p.get("tab", view if view != "faq" else "faq")
        if tab:
            s = s.replace(f'class="tab" id="t-{tab}"', f'class="tab" id="t-{tab}" aria-current="page"', 1)
        slots = p.get("slots", {})
        home = view == "route"
        defaults = {
            "ageopts": self.age_options() if home else "",
            "exrow": self.ex_row() if home else "",
            "gloss": self.gloss() if home else "",
            "footchecked": e(t("foot.checked", date=fmt_day(self.last_checked))),
            "schoolattrs": "",
            "homelinks": "",
        }
        defaults.update(slots)
        for k, v in defaults.items():
            s = s.replace(f"<!--@{k}-->", v)
        s = re.sub(r"<!--@\w+-->", "", s)
        assert "<!--@" not in s
        s = re.sub(r"\n\s*", "\n", s)
        return s

    def write(self, rel, content):
        path = self.out_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf8", newline="\n")
        self.pages += 1

    # ------------------------------------------------------------ static fragments shared with the shell
    def age_options(self):
        t = self.t
        o = [f'<option value="">{e(t("form.agePlaceholder"))}</option>', f'<option value="u4">{e(t("form.ageU4"))}</option>']
        for a in range(4, 18):
            o.append(f'<option value="{a}">{e(t("form.ageN", age=str(a)))}</option>')
        o.append(f'<option value="18">{e(t("form.age18"))}</option>')
        return "".join(o)

    def ex_row(self):
        t = self.t
        o = [f'<span class="exlbl">{e(t("form.tryExample"))}</span>']
        for pc, k in (("1077", "amsterdam"), ("2517", "hague"), ("5611", "eindhoven")):
            o.append(f'<button class="chip exbtn" type="button">{e(t("ex." + k))}</button>')
        return "".join(o)

    def gloss(self):
        return "".join(f"<dt>{e(a)}</dt><dd>{e(b)}</dd>" for a, b in self.en["glossary"])

    def crumbs(self, items):
        t = self.t
        li = []
        for i, (label, href) in enumerate(items):
            if href and i < len(items) - 1:
                li.append(f'<li><a href="{e(href)}">{e(label)}</a></li>')
            else:
                li.append(f'<li><span aria-current="page">{e(label)}</span></li>')
        return f'<nav class="crumbs" aria-label="{e(t("crumb.aria"))}"><ol>{"".join(li)}</ol></nav>'

    def src_line(self, keys, cls="src"):
        t = self.t
        parts = []
        for k in keys:
            u = self.src_url.get(k)
            if not u:
                continue
            parts.append(f'<a href="{e(u)}" target="_blank" rel="noopener">{e(t("src." + k))}</a>')
        return f'<p class="{cls}">{e(t("src.label"))} ' + " · ".join(parts) + "</p>"

    # ------------------------------------------------------------ description fitting
    @staticmethod
    def fit(base, opts, tails, lo=150, hi=160):
        """base + a subset of opts (kept in order) + up to two tails, 150 to 160 characters; most complete text first"""
        from itertools import combinations
        best = None
        n = len(opts)
        for k in range(n, -1, -1):
            for pick in combinations(range(n), k):
                head = [base] + [opts[i] for i in pick]
                cands = [[]] + [[x] for x in tails] + [[x, y] for x, y in combinations(tails, 2)]
                for tl in cands:
                    txt = " ".join(head + tl)
                    L = len(txt)
                    if lo <= L <= hi:
                        return txt
                    if L <= hi and (best is None or L > len(best)):
                        best = txt
        if best is None:
            best = base[: hi - 3].rsplit(" ", 1)[0] + "..."
        return best

    # ------------------------------------------------------------ system svg (port of buildSystem in app.js)
    def system_svg(self):
        t = self.t
        W, H = 360, 700
        o = []

        def rect(x, y, w, hh, cls, txt=None, tcls="on"):
            o.append(f'<rect class="cell {cls}" x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(hh)}"/>')
            if txt not in (None, ""):
                o.append(f'<text class="{tcls}" x="{num(x + w / 2)}" y="{num(y + hh / 2 + 4)}" text-anchor="middle">{e(txt)}</text>')

        def text(x, y, tx, cls="ax", anchor=None):
            a = f' text-anchor="{anchor}"' if anchor else ""
            o.append(f'<text class="{cls}" x="{num(x)}" y="{num(y)}"{a}>{e(tx)}</text>')

        def path(d, dash=False, both=False):
            o.append(f'<path class="arh" d="{d}"/>')
            ms = ' marker-start="url(#ah)"' if both else ""
            o.append(f'<path class="ar{" d" if dash else ""}" d="{d}" marker-end="url(#ah)"{ms}/>')

        def mk(cx, y, tx):
            o.append(f'<rect class="mkb" x="{num(cx - 7)}" y="{num(y)}" width="14" height="14"/>')
            o.append(f'<text class="mkt" x="{num(cx)}" y="{num(y + 10.5)}" text-anchor="middle">{e(tx)}</text>')

        def bar(x, y, w, n, cls, labels=None):
            for i in range(n):
                rect(x, y + i * 20, w, 20, cls, labels[i] if labels else str(i + 1))

        o.append(f'<svg class="sys-svg" viewBox="0 0 {W} {H}" role="img" aria-labelledby="sysT sysD" style="direction:ltr">')
        o.append(f'<title id="sysT">{e(t("sys.title"))}</title><desc id="sysD">{e(t("sys.desc"))}</desc>')
        o.append('<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="13" markerHeight="13" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path class="ah" d="M0 0L10 5L0 10z"/></marker></defs>')
        LX = [40, 120, 200, 280]
        LW = 60
        C = [70, 150, 230, 310]
        text(40, 14, t("sys.primary"), "ax")
        for g in range(1, 9):
            y = 22 + (g - 1) * 20
            rect(40, y, 308, 20, "f-bo")
            o.append(f'<text class="on" x="48" y="{num(y + 14.5)}">{e(t("sys.yearGroup", n=str(g)))}</text>')
            o.append(f'<text class="on" x="340" y="{num(y + 14.5)}" text-anchor="end">{e(t("sys.age", n=str(g + 3)))}</text>')
        for x in C:
            path(f"M{x} 184V230")
        o.append('<rect class="lbl" x="36" y="196" width="288" height="24"/>')
        mk(50, 201, "1")
        text(64, 213, t("sys.adviceLabel"), "ax")
        names = ["pro", "vmbo", "havo", "vwo"]
        cls = ["f-pro", "f-vbk", "f-havo", "f-vwo"]
        yrs = [5, 4, 5, 6]
        text(34, 246, t("sys.ageAxis"), "ax", "end")
        for i in range(4):
            rect(LX[i], 232, LW, 18, cls[i], t("sys.lane." + names[i]), "hd")
            bar(LX[i], 250, LW, yrs[i], cls[i])
        for k, a in enumerate([12, 14, 16, 18]):
            text(34, 250 + k * 40 + 14, str(a), "ax", "end")
        path("M181 278H199", True, True)
        path("M261 278H279", True, True)
        mk(190, 284, "2")
        mk(270, 284, "2")
        path("M181 314H199", True)
        mk(190, 320, "3")
        path("M261 334H279")
        mk(270, 340, "4")
        path("M70 352V424", True)
        mk(70, 380, "5")
        path("M150 332V424")
        mk(150, 380, "6")
        path("M230 352V424")
        mk(230, 396, "7")
        path("M214 352V392H166V424")
        mk(190, 385, "7")
        path("M310 372V424")
        mk(310, 396, "8")
        path("M296 372V404H258V424")
        mk(277, 397, "8")
        rect(40, 424, 132, 18, "f-mbo", "mbo", "hd")
        rect(200, 424, 62, 18, "f-hbo", "hbo", "hd")
        rect(280, 424, 68, 18, "f-wo", "wo", "hd")
        for k, l in enumerate([1, 2, 3, 4]):
            lb = [str(l) if q == 0 else "" for q in range(l)]
            bar(40 + k * 34, 442, 30, l, "f-mbo", lb)
        text(106, 540, t("sys.mboLevels"), "ax", "middle")
        bar(200, 442, 22, 2, "f-hbo", ["AD", ""])
        bar(226, 442, 36, 4, "f-hbo")
        path("M244 523V543", True)
        bar(226, 544, 36, 2, "f-hbo", ["M", ""])
        bar(280, 442, 68, 3, "f-wo")
        path("M314 503V525", True)
        bar(280, 526, 68, 2, "f-wo", ["M", ""])
        path("M314 567V589", True)
        bar(280, 590, 68, 4, "f-wo", ["PhD", "", "", ""])
        path("M173 470H199")
        mk(186, 477, "a")
        path("M263 452H279", True)
        mk(271, 458, "b")
        path("M263 512H271V536H279", True)
        mk(271, 519, "d")
        text(36, 692, t("sys.legend"), "ax")
        o.append("</svg>")
        return "".join(o)

    def system_slots(self):
        t = self.t
        keys = "".join(f'<li><i style="background:var(--c-{x})"></i>{e(t("sys.key." + x))}</li>' for x in ["bo", "pro", "vbk", "havo", "vwo", "mbo", "hbo", "wo"])
        xf = "".join(f'<li><b>{e(x["k"])}</b><span>{e(x["text"])}</span></li>' for x in self.en["sys"]["xfers"])
        xf += f'<li><b>+</b><span>{e(t("sys.xfersExtra"))}</span></li>'
        links = []
        for key in ["schema", "nuf", "loket", "gov", "mboRijks", "sk123", "vo_raad_moving_from_vmbo_to_havo_and_fro", "rijksoverheid_which_diplomas_give_access"]:
            links.append(f'<a href="{e(self.src_url[key])}" target="_blank" rel="noopener">{e(t("src." + key))}</a>')
        syssrc = e(t("src.label")) + " " + " · ".join(links)
        return {"sysfig": self.system_svg(), "syskeys": keys, "xfers": xf, "syssrc": syssrc}

    # ------------------------------------------------------------ faq
    def faq_html(self):
        t = self.t
        groups = self.en["faq"]["groups"]
        o = ['<div class="faqtools"><nav class="faqnav" aria-label="%s">' % e(t("faq.navAria"))]
        for g in groups:
            o.append(f'<a class="chip" href="#faqg-{e(g["id"])}" style="text-decoration:none">{e(g["title"])}</a>')
        o.append("</nav>")
        o.append(f'<div class="faqall"><button class="btn sec" type="button">{e(t("faq.expand"))}</button> <button class="btn sec" type="button">{e(t("faq.collapse"))}</button></div></div>')
        for g in groups:
            o.append(f'<section class="faqgrp" aria-labelledby="faqg-{e(g["id"])}"><h2 id="faqg-{e(g["id"])}">{e(g["title"])}</h2>')
            for x in g["items"]:
                o.append(f'<details id="{e(x["id"])}" open><summary>{e(x["q"])}</summary><div class="ans">')
                for b in x["blocks"]:
                    if "p" in b:
                        o.append(f"<p>{rich(b['p'])}</p>")
                    elif "say" in b:
                        o.append(f'<p class="say">{rich(b["say"])}</p>')
                    elif "ul" in b:
                        o.append("<ul>" + "".join(f"<li>{rich(li)}</li>" for li in b["ul"]) + "</ul>")
                o.append(self.src_line(x.get("src", [])))
                o.append(f'<p class="faqlink"><a href="{self.href("questions/#" + x["id"])}">{e(t("faq.link"))}</a></p></div></details>')
            o.append("</section>")
        return "".join(o)

    def faq_jsonld(self):
        qs = []
        for g in self.en["faq"]["groups"]:
            for x in g["items"]:
                parts = []
                for b in x["blocks"]:
                    if "p" in b:
                        parts.append("<p>" + e(re.sub(r"</?b>", "", b["p"])) + "</p>")
                    elif "say" in b:
                        parts.append("<p>" + e(re.sub(r"</?b>", "", b["say"])) + "</p>")
                    elif "ul" in b:
                        parts.append("<ul>" + "".join("<li>" + e(re.sub(r"</?b>", "", li)) + "</li>" for li in b["ul"]) + "</ul>")
                qs.append({"@type": "Question", "name": x["q"], "acceptedAnswer": {"@type": "Answer", "text": "".join(parts)}})
        return {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": self.langs[0], "mainEntity": qs}

    # ------------------------------------------------------------ sources (port of renderSources)
    def sources_html(self):
        t = self.t
        m = self.meta
        o = []
        o.append(f'<div class="psec"><h2>{e(t("sources.check.title"))}</h2><p>{e(t("sources.check.text", date=fmt_day(self.last_checked)))}</p></div>')
        o.append(f'<div class="psec"><h2>{e(t("sources.read.title"))}</h2>' + "".join(f"<p>{e(x)}</p>" for x in self.en["sources"]["read"]["items"]) + "</div>")
        d = [f'<div class="psec"><h2>{e(t("sources.data.title"))}</h2>']
        att = m.get("attribution")
        if att:
            d.append(f'<p>{e(t("sources.dataline", built=m.get("generated", ""), pupils=self.data_year("po_pupils")[1], advice=self.data_year("po_advice")[0], exams=self.data_year("vo_exams")[0]))}</p>')
        d.append('<ul class="srclist">')
        li = [e(t("attr.feat.lead")) + " "]
        for i, (k, url, lic) in enumerate(self.feat_attr):
            if i:
                li.append(", ")
            li.append(f'<a href="{e(url)}" target="_blank" rel="noopener">{e(t("attr.l." + k))}</a>')
            if lic:
                li.append(e(" (" + lic + ")"))
        li.append(" " + e(t("attr.feat.tail")))
        d.append("<li>" + "".join(li) + "</li>")
        if att:
            for a in att:
                d.append(f'<li>{e(a["text"] + " " + t("attr.licence", licence=a["licence"]) + " ")}<a href="{e(a["licence_url"])}" target="_blank" rel="noopener">{e(t("attr.licenceLink"))}</a> · <a href="{e(a["url"])}" target="_blank" rel="noopener">{e(t("attr.sourceLink"))}</a></li>')
            d.append("</ul>")
            if m.get("disclaimer"):
                d.append(f'<p>{e(m["disclaimer"])}</p>')
        else:
            d.append(f'<li>{e(t("attr.fallback"))}</li></ul><p>{e(t("attr.fallbackDisc"))}</p>')
        d.append(f'<p>{e(t("sources.sodk"))}</p></div>')
        o.append("".join(d))
        # blocks
        b = [f'<div class="psec"><h2>{e(t("sources.blocks.title"))}</h2><p>{e(t("sources.blocks.intro"))}</p><ul class="srclist">' + "".join(f"<li>{e(x)}</li>" for x in self.en["sources"]["blocks"]["items"]) + "</ul>"]
        c = m.get("counts") or {}
        if isinstance(c.get("schools_po"), int):
            b.append(f'<p>{e(t("sources.counts.schools", po=c["schools_po"] - (c.get("schools_po_sbo") or 0), sbo=c.get("schools_po_sbo") or 0, so=c.get("schools_so") or 0, vo=c.get("schools_vo") or 0))}</p>')
        I = self.insp
        k = I.get("counts") or {}
        if isinstance(k.get("listed"), int):
            by = ""
            bo = k.get("by_o")
            if isinstance(bo, dict):
                by = ", ".join(f"{j} {nf(bo[j])}" for j in ["Goed", "Voldoende", "Onvoldoende", "Zwak", "Zeer zwak"] if isinstance(bo.get(j), int))
            txt = t("sources.counts.insp", listed=k["listed"], rated=k["rated"], none=k["geen_eindoordeel"], basic=k["basistoezicht"], asof=I.get("as_of", "")) + (" " + t("sources.counts.by", by=by) if by else "")
            b.append(f"<p>{e(txt)}</p>")
            links = []
            if self.safe_url(I.get("source_url")):
                links.append(f'<a href="{e(I["source_url"])}" target="_blank" rel="noopener">{e(t("sources.insp.file"))}</a>')
            if self.safe_url(I.get("notes_url")):
                links.append(f'<a href="{e(I["notes_url"])}" target="_blank" rel="noopener">{e(t("sources.insp.notes"))}</a>')
            if links:
                b.append('<p class="dsrc">' + " · ".join(links) + "</p>")
        b.append("</div>")
        o.append("".join(b))
        lst = "".join(f'<li><a href="{e(self.src_url[k])}" target="_blank" rel="noopener">{e(t("src." + k))}</a></li>' for k in self.src_order)
        o.append(f'<div class="psec"><h2>{e(t("sources.list.title"))}</h2><ul class="srclist">{lst}</ul></div>')
        return "".join(o)

    # ------------------------------------------------------------ home links
    def province_tops(self):
        by = {}
        for s in self.schools:
            if not s["mun"] or not s["provN"]:
                continue
            by.setdefault((s["provN"], s["mun"]), []).append(s)
        best = {}
        for (prov, mun), lst in by.items():
            n = len(lst)
            if prov not in best or n > best[prov][1] or (n == best[prov][1] and mun < best[prov][0]):
                best[prov] = (mun, n)
        return sorted((p, m, n) for p, (m, n) in best.items())

    def home_links(self, tops):
        t = self.t
        o = [f'<h3>{e(t("home.linksTitle"))}</h3><p>{e(t("home.linksIntro"))}</p><ul class="provs">']
        for prov, mun, n in tops:
            o.append(f'<li><a href="{self.href("municipality/" + self.mslug[mun] + "/")}">{e(mun)}<small>{e(prov)}</small></a></li>')
        o.append("</ul>")
        o.append(f'<p><a href="{self.href("municipalities/")}">{e(t("home.linksAll"))}</a> &middot; <a href="{self.href("find/")}">{e(t("home.linksFind"))}</a> &middot; <a href="{self.href("questions/")}">{e(t("home.linksQuestions"))}</a></p>')
        return "".join(o)

    # ------------------------------------------------------------ school page
    def school_page(self, s, near):
        t = self.t
        sec = s["sec"]
        grp = "vo" if sec == "vo" else "so" if sec == "so" else "po"
        den = self.den_label(s["denNl"])
        slug = school_slug(s)
        rel = f"school/{slug}/"
        pc = s["pc"]
        pc_fmt = (pc[:4] + " " + pc[4:]) if pc and len(pc) == 6 else (pc or "")
        typ = t("seo.type." + sec)
        k1 = (s["name"], s["city"], s["sec"])
        dup = self.tcount[k1] > 1 and bool(s["addr"])
        if dup:
            addr_t = s["addr"] + (f" ({s['id']})" if self.tcount[k1 + (s["addr"],)] > 1 else "")
            title = t("title.schoolAddr", name=s["name"], type=typ, city=s["city"], addr=addr_t)
        else:
            title = t("title.school" if s["city"] else "title.schoolNoCity", name=s["name"], type=typ, city=s["city"])
        det = (self.det_vo if grp == "vo" else self.det_po)["schools"].get(s["id"]) if grp != "so" else None
        pur = {"po": "po_pupils", "sbo": "po_pupils", "vo": "vo_pupils", "so": "so_pupils"}[sec]
        pup_range, pup_date = self.data_year(pur)
        # --- description
        if s["pupils"] is None:
            pup_txt = None
        else:
            ptxt = t("pupils.atLeast" if s["pupils_lb"] else "pupils.about", n=s["pupils"])
            pup_txt = ptxt[0].upper() + ptxt[1:] + "."
        opts = []
        if dup:
            opts.append(t("seo.desc.addr", addr=s["addr"]))
        if pup_txt:
            opts.append(pup_txt)
        opts.append(t("seo.desc.den", den=den))
        if sec == "vo":
            names = self.track_names(s)
            if names:
                opts.insert(1, t("seo.desc.tracks", tracks=", ".join(names)))
        if sec == "so":
            cl = s.get("cls") or ([s["cl"]] if s.get("cl") is not None else [])
            if cl:
                opts.insert(1, t("seo.desc.cluster", cluster=" and ".join(t(f"so.cl.{c}.chip") for c in cl)))
        base = t("seo.desc.school" if s["city"] else "seo.desc.schoolNoCity", name=s["name"], type=typ, city=s["city"], prov=s["provN"])
        if not s["provN"]:
            base = base.replace(" ()", "").replace("()", "")
        if len(base) > 156:
            nm = s["name"]
            cut = nm[: max(20, len(nm) - (len(base) - 150))].rsplit(" ", 1)[0] + "..."
            base = base.replace(nm, cut)
        desc = self.fit(base, opts, self.en["seo"]["desc"]["tail"])

        # --- phead
        mrel = f"municipality/{self.mslug[s['mun']]}/" if s["mun"] else None
        crumbs = [(t("crumb.home"), self.href(""))]
        if mrel:
            crumbs.append((s["mun"], self.href(mrel)))
        crumbs.append((s["name"], None))
        ph = ['<div class="phead">', self.crumbs(crumbs)]
        ph.append(f'<a class="back" href="{self.href("find/")}">{e(t("school.back"))}</a>')
        ph.append(f'<div class="when">{e(t("sec.long." + sec))}</div>')
        ph.append(f'<h1 id="h-school" tabindex="-1">{e(s["name"])}</h1>')
        if sec == "so":
            tg = ""
            if s.get("so_type"):
                tg += f'<span class="tr t-so">{e(s["so_type"])}</span>'
            for c in (s.get("cls") or ([s["cl"]] if s.get("cl") is not None else [])):
                tg += f'<span class="tr t-socl">{e(t(f"so.cl.{c}.chip"))}</span>'
            ph.append(f'<div style="margin:0 0 6px">{tg}</div>')
        addr = ", ".join(x for x in [s["addr"], " ".join(x for x in [pc_fmt, s["city"]] if x), t("school.municipality", mun=s["mun"]) if s["mun"] and s["mun"] != s["city"] else None] if x)
        ph.append(f'<p class="addr">{e(addr)}</p>')
        isk = bool(sec == "vo" and (re.search(r"\bISK\b|schakelklas|internationale schakel", s["name"], re.I) or s.get("st") == "BRUGJAAR"))
        ph.append(f'<p style="margin:0 0 6px">{e(t("school.denom", den=den) + (t("school.isk") if isk else ""))}</p>')
        ph.append(self.feat_chips(s["id"]))
        lk = ['<div class="lk">']
        if sec != "so":
            q = re.sub(r"\s+", " ", (s["name"] + " " + s["city"])).strip()
            from urllib.parse import quote
            lk.append(f'<a href="https://scholenopdekaart.nl/zoeken/{"basisscholen" if grp == "po" else "middelbare-scholen"}?zoektermen={quote(q, safe="")}&amp;weergave=Lijst" target="_blank" rel="noopener">{e(t("link.sodk"))}</a>')
        w = self.safe_web(s["web"])
        if w:
            lk.append(f'<a href="{e(w)}" target="_blank" rel="noopener">{e(t("link.site"))}</a>')
        if s["g"] != 3 and s["lat"] is not None:
            lk.append(f'<a href="{self.href("map/?s=" + s["id"])}">{e(t("school.showMap"))}</a>')
        lk.append("</div>")
        ph.append("".join(lk))
        if 0 < s["g"] < 3:
            ph.append(f'<p class="note">{e(t("school.approx"))}</p>')
        ph.append("</div>")

        def psec(title, expl, kids, src=None):
            o = [f'<section class="psec"><h2>{e(title)}</h2>']
            if expl:
                o.append(f'<p class="expl"><b>{e(t("prof.whatMeans"))}</b>{e(expl)}</p>')
            o.extend(kids)
            if src:
                o.append(f'<p class="dsrc">{e(src)}</p>')
            o.append("</section>")
            return "".join(o)

        def duo_src(what_key, rng, date):
            return t("prof.duoSrc", what=t(what_key)) + ((": " + (rng or "") + ((" " + t("prof.counted", date=date)) if date else "")) if (rng or date) else "") + "."

        secs = []
        # pupils
        big = t("prof.pupils.notShown") if s["pupils"] is None else (t("prof.pupils.bigAtLeast", n=s["pupils"]) if s["pupils_lb"] else nf(s["pupils"]))
        pk = [f'<div class="big">{e(big)}</div>']
        pk.append(f'<p class="note" style="margin-top:4px">{e(t("prof.pupils.noCount") if s["pupils"] is None else t("prof.pupils.total") + ((" " + t("prof.pupils.hiddenNote")) if s["pupils_lb"] else ""))}</p>')
        secs.append(psec(t("prof.pupils.title"), t("prof.pupils.expl"), pk, duo_src("prof.pupils.srcWhat", pup_range, pup_date)))
        if sec == "vo":
            kids = []
            tb = self.track_badges(s)
            kids.append(f"<div>{tb or '<span class=\"note\">' + e(t('prof.levels.none')) + '</span>'}</div>")
            if s.get("st"):
                kids.append(f'<p class="note">{e(t("prof.levels.st", st=s["st"]))}</p>')
            rng, date = self.data_year("vo_pupils")
            secs.append(psec(t("prof.levels.title"), t("prof.levels.expl"), kids, duo_src("prof.levels.srcWhat", rng, date) + " " + t("prof.levels.fromPupilFile")))
            # latest pass rate per track
            kids = []
            pr = (det or {}).get("pr") if det else None
            order = ["PRO", "VMBO-B", "VMBO-K", "VMBO-GL/TL", "HAVO", "VWO", "BRUGJAAR"]
            tkmap = {"PRO": ("pro", "pro"), "VMBO-B": ("bb", "bb"), "VMBO-K": ("kb", "kb"), "VMBO-GL/TL": ("gt", "tl"), "HAVO": ("havo", "havo"), "VWO": ("vwo", "vwo"), "BRUGJAAR": ("bridge", "ib")}
            passrows = []
            if pr:
                for k in order:
                    arr = pr.get(k)
                    if not arr:
                        continue
                    row = sorted(arr, key=lambda r: str(r[0]))[-1]
                    nm, cl = tkmap[k]
                    passrows.append((nm, cl, row))
                for nm, cl, row in passrows:
                    if row[2] is None:
                        txt = t("prof.pass.few")
                    else:
                        txt = t("exam.rowPass", pct=jr(row[2]), n=row[1]) + ((" " + t("prof.pass.partial")) if len(row) > 3 and row[3] else "") + ((" " + t("prof.pass.small")) if row[1] is not None and row[1] < 30 else "")
                    kids.append(f'<div><span class="tr t-{cl}">{e(t("tk." + nm))}</span> {e(t("prof.pass.year", y=str(row[0])))}: {e(txt)}</div>')
            elif s.get("exam"):
                for ex in s["exam"]:
                    if ex[1] is None:
                        rest = t("exam.hidden")
                    elif ex[1] < 30:
                        rest = t("exam.few", n=ex[1]) + (t("exam.partial") if ex[3] else "")
                    else:
                        rest = t("exam.pass", pct=jr(ex[2]), n=ex[1]) + (t("exam.partial") if ex[3] else "")
                    bd = t("badge." + ex[0]) if self.t.has("badge." + ex[0]) else ex[0]
                    kids.append(f'<div><span class="tr t-{ex[0]}">{e(bd)}</span> {e(rest)}</div>')
            rng, date = self.data_year("vo_exams")
            if kids:
                secs.append(psec(t("prof.pass.title"), t("prof.pass.expl"), kids, duo_src("prof.pass.srcWhat", rng, date)))
            else:
                secs.append(psec(t("prof.pass.title"), t("prof.pass.explShort"), [f'<p class="note">{e(t("prof.pass.none"))}</p>'], duo_src("prof.pass.srcWhat", rng, date)))
        elif sec in ("po", "sbo"):
            if sec == "po":
                rng, date = self.data_year("po_advice")
                secs.append(psec(t("prof.advice.title"), t("prof.advice.expl"), [self.advice_block(s["adv"])], duo_src("prof.advice.srcWhat", rng, date)))
            else:
                secs.append(psec(t("prof.sbo.title"), t("prof.sbo.text"), [], None))
        else:
            kv = []
            cls = s.get("cls") or ([s["cl"]] if s.get("cl") is not None else [])
            sot = s.get("so_type")
            kv.append((t("prof.so.type"), t("so.type." + ("both" if sot == "SO/VSO" else "vso" if sot == "VSO" else "so"))))
            kv.append((t("prof.so.cluster"), " · ".join(t(f"so.cl.{c}.name") for c in cls) if cls else t("prof.so.clusterNone")))
            kvh = '<div class="kv stack">' + "".join(f'<div class="r"><span>{e(a)}</span><span>{e(b)}</span></div>' for a, b in kv) + "</div>"
            dl = ""
            if cls:
                dl = '<dl class="dl">' + "".join(f'<dt>{e(t(f"so.cl.{c}.name"))}</dt><dd>{e(t(f"so.cl.{c}.desc"))}</dd>' for c in cls) + "</dl>"
            secs.append(psec(t("prof.so.title"), t("prof.so.expl"), [kvh, dl], None))
        # inspection
        secs.append(self.insp_section(s, psec))
        # nearby
        if near:
            li = []
            for o, d in near:
                sub = " · ".join(x for x in [o["city"], self.den_label(o["denNl"])] if x)
                dist = t("unit.lessThanOne") if d < 1 else (nf1(d) if d < 10 else nf(jr(d)))
                li.append(f'<li><span><a href="{self.href("school/" + school_slug(o) + "/")}">{e(o["name"])}</a><div class="note" style="margin:0">{e(sub)}</div></span><span class="d">{e(t("unit.km", n=dist))}</span></li>')
            secs.append(psec(t("prof.nb.title." + sec), t("prof.nb.expl"), ['<ul class="nb-list">' + "".join(li) + "</ul>"], t("prof.nb.src")))
        main = "".join(ph) + '<div class="pgrid">' + "".join(secs) + "</div>" + f'<p class="note">{e(t("school.note"))}</p>'

        # --- json-ld
        ldtype = {"po": "ElementarySchool", "sbo": "ElementarySchool", "vo": "HighSchool", "so": "School"}[sec]
        ld = {"@context": "https://schema.org", "@type": ldtype, "name": s["name"], "url": self.canon(rel)}
        adr = {"@type": "PostalAddress", "addressCountry": "NL"}
        if s["addr"]:
            adr["streetAddress"] = s["addr"]
        if pc_fmt:
            adr["postalCode"] = pc_fmt
        if s["city"]:
            adr["addressLocality"] = s["city"]
        if s["provN"]:
            adr["addressRegion"] = s["provN"]
        ld["address"] = adr
        if s["g"] is not None and s["g"] < 2 and s["lat"] is not None:
            ld["geo"] = {"@type": "GeoCoordinates", "latitude": s["lat"], "longitude": s["lon"]}
        if w:
            ld["sameAs"] = [w]
        bl = [{"@type": "ListItem", "position": 1, "name": t("crumb.home"), "item": self.canon("")}]
        pos = 2
        if mrel:
            bl.append({"@type": "ListItem", "position": pos, "name": s["mun"], "item": self.canon(mrel)})
            pos += 1
        bl.append({"@type": "ListItem", "position": pos, "name": s["name"], "item": self.canon(rel)})
        bcl = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": bl}
        return {
            "rel": rel, "view": "school", "tab": "find", "title": title, "desc": desc, "jsonld": [ld, bcl],
            "slots": {"school": main, "schoolattrs": f' data-static="{e(s["id"])}"'},
        }

    def track_names(self, s):
        tr = s.get("tracks") or 0
        names = []
        if tr & 1:
            names.append(self.t("tk.pro"))
        if tr & 2:
            names.append(self.t("tk.bb"))
        if tr & 4:
            names.append(self.t("tk.kb"))
        if tr & 24:
            names.append(self.t("tk.gt"))
        if tr & 32:
            names.append(self.t("tk.havo"))
        if tr & 64:
            names.append(self.t("tk.vwo"))
        return names

    def track_badges(self, s):
        t = self.t
        tr = s.get("tracks") or 0
        defs = [("pro", 1), ("bb", 2), ("kb", 4), ("gl", 8), ("tl", 16), ("havo", 32), ("vwo", 64), ("gym", 128), ("ib", 512), ("ess", 1024)]
        out = "".join(f'<span class="tr t-{k}">{e(t("badge." + k))}</span>' for k, b in defs if tr & b)
        groups = (1 if tr & 30 else 0) + (1 if tr & 32 else 0) + (1 if tr & 64 else 0)
        if groups >= 2:
            out += f'<span class="broad">{e(t("broad", n=groups))}</span>'
        return out

    def advice_block(self, a):
        t = self.t
        if not a or not a[2] or a[0] < 15 or a[1] > 6:
            txt = t("adv.hidden", n=a[0], hidden=a[1]) if a and a[0] > 0 else t("adv.none")
            return f'<div class="adv"><p class="advn">{e(txt)}</p></div>'
        sh = a[2]
        seg = [("pro", [0, 1]), ("vbk", [2, 3, 4]), ("vgt", [5, 6]), ("havo", [7, 8]), ("vwo", [9, 10])]
        parts = []
        bar = []
        for k, idx in seg:
            v = sum((sh[i] or 0) for i in idx)
            if v > 0:
                bar.append(f'<i class="a-{k}" style="width:{num(round(v, 6))}%"></i>')
                parts.append((v, t("adv.part", label=t("seg." + k), pct=jr(v))))
        parts.sort(key=lambda x: -x[0])
        summ = t("sep.list").join(p for _, p in parts)
        return (f'<div class="adv"><div class="bar" role="img" aria-label="{e(t("adv.aria", list=summ))}">{"".join(bar)}</div>'
                f'<div class="advn">{e(t("adv.line", list=summ, n=a[0]) + (t("adv.partial") if a[1] > 0 else ""))}</div></div>')

    def insp_section(self, s, psec):
        t = self.t
        I = self.insp
        r = I["schools"].get(s["id"])
        sector = "VO" if s["sec"] == "vo" else "SO" if s["sec"] == "so" else "PO"
        brin = s["id"][:4]
        tpl = I.get("deeplink") or ""
        link = tpl.replace("{BRIN4}", brin).replace("{SECTOR}", sector)
        if not link.startswith("https://toezichtresultaten.onderwijsinspectie.nl/"):
            link = f"https://toezichtresultaten.onderwijsinspectie.nl/extern?code={brin}&sector={sector}"
        btn = (f'<div style="margin-top:12px"><a class="btn lnk" href="{e(link)}" target="_blank" rel="noopener">{e(t("insp.btn"))}<span class="sr"> {e(t("insp.btnNew"))}</span></a>'
               f'<p class="note">{e(t("insp.btnNote", brin=brin))}</p></div>')
        rated = ["Goed", "Voldoende", "Onvoldoende", "Zwak", "Zeer zwak"]
        warn = ["Onvoldoende", "Zeer zwak", "Zwak", "Voldoet niet"]
        kids = []
        if r and r.get("o") in rated:
            w = " warn" if r["o"] in warn else ""
            box = f'<div class="insp{w}"><b>{e(r["o"])}</b>'
            gl = (I.get("scale") or {}).get(r["o"])
            if gl:
                box += f'<div class="note" style="margin:2px 0 0">{e(gl)}</div>'
            xk = [k for k, v in (r.get("x") or {}).items() if isinstance(v, str)]
            if xk:
                box += f'<div class="note" style="margin:2px 0 0">{e(t("prof.insp.lowest"))}</div>'
            if r.get("d"):
                box += f'<div class="note" style="margin:2px 0 0">{e(t("prof.insp.dated", date=r["d"]))}</div>'
            box += "</div>"
            kids.append(box)
            if xk:
                lis = ""
                for k in xk:
                    key = re.sub(r"[^A-Za-z]", "", k)
                    nm = t("insp.prog." + key) if t.has("insp.prog." + key) else k
                    lis += f"<li><span>{e(nm)}</span><span>{e(r['x'][k])}</span></li>"
                kids.append(f'<div><b>{e(t("insp.perProg"))}</b><ul class="progs">{lis}</ul></div>')
            kids.append(btn)
            src = I.get("source", "")
            kids.append(f'<p class="dsrc">{e(t("prof.insp.source"))} {e(src)}' + (". " + e(t("prof.insp.asOf", date=I.get("as_of", ""))) if I.get("as_of") else "") + ".</p>")
        elif r and r.get("o") in ("Geen eindoordeel", "Basistoezicht"):
            gk = "basic" if r["o"] == "Basistoezicht" else "none"
            kids.append(f'<div class="insp nofinal"><b>{e(t("insp.nf." + gk + ".title"))}</b><div class="note" style="margin:4px 0 0">{e(t("insp.nf." + gk + ".expl"))}</div></div>')
            kids.append(btn)
        else:
            kids.append(f'<p>{e(t("prof.insp.none"))} <a href="https://www.onderwijsinspectie.nl/" target="_blank" rel="noopener">{e(t("prof.insp.linkText"))}</a>.</p>')
            kids.append(btn)
        return psec(t("prof.insp.title"), t("prof.insp.expl"), kids, None)

    # ------------------------------------------------------------ municipality pages
    def muni_pages(self, by_mun):
        t = self.t
        for mun, lst in sorted(by_mun.items()):
            slug = self.mslug[mun]
            rel = f"municipality/{slug}/"
            prov = max(set(s["provN"] for s in lst), key=lambda p: sum(1 for s in lst if s["provN"] == p))
            counts = {k: sum(1 for s in lst if s["sec"] == k) for k in ("po", "sbo", "vo", "so")}
            tot = sum((s["pupils"] or 0) for s in lst)
            parts = [t(f"muni.parts.{k}", n=counts[k]) for k in ("po", "sbo", "vo", "so") if counts[k]]
            plist = ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]
            intro = t("muni.intro", name=mun, prov=prov, n=len(lst), parts=plist)
            intro2 = t("muni.introPupils", n=tot) if tot else ""
            pcs = {}
            for s in lst:
                if s["pc"] and len(s["pc"]) >= 4:
                    pcs[s["pc"][:4]] = pcs.get(s["pc"][:4], 0) + 1
            top_pc = sorted(pcs.items(), key=lambda x: (-x[1], x[0]))[0][0] if pcs else None
            h1 = t("muni.h1", name=mun)
            cr = [(t("crumb.home"), self.href("")), (t("muni.crumbList"), self.href("municipalities/")), (mun, None)]
            o = [f'<div class="phead">{self.crumbs(cr)}<h1 class="vh" id="h-static" tabindex="-1">{e(h1)}</h1><p>{e(intro)} {e(intro2)}</p>']
            if top_pc:
                o.append(f'<p><a class="btn lnk" href="{self.href("?pc=" + top_pc)}">{e(t("muni.routeLink", pc=top_pc))}</a></p><p class="note">{e(t("muni.routeText"))}</p>')
            o.append("</div>")
            for k in ("po", "sbo", "vo", "so"):
                grp = sorted((s for s in lst if s["sec"] == k), key=lambda s: (s["name"].lower(), s["id"]))
                if not grp:
                    continue
                li = []
                for s in grp:
                    if s["pupils"] is None:
                        pu = t("muni.noCount")
                    else:
                        pu = t("muni.pupilsAtLeast" if s["pupils_lb"] else "muni.pupilsAbout", n=s["pupils"])
                    facts = [s["city"] + (", " + s["addr"] if s["addr"] else "") if s["city"] else s["addr"], pu]
                    if k == "vo":
                        names = self.track_names(s)
                        if names:
                            facts.append(", ".join(names))
                    if k == "so" and s.get("so_type"):
                        facts.append(s["so_type"])
                    li.append(f'<li><a href="{self.href("school/" + school_slug(s) + "/")}">{e(s["name"])}</a><span class="mt">{e(" · ".join(x for x in facts if x))}</span></li>')
                o.append(f'<section class="psec"><h2>{e(t("muni.group." + k, name=mun))}</h2><p class="expl">{e(t("muni.groupNote." + k))}</p><ul class="muni-list">{"".join(li)}</ul></section>')
            o.append(f'<p class="note">{e(t("muni.src"))}</p>')
            title = t("title.municipality", name=mun)
            base = t("seo.desc.municipality", name=mun, prov=prov, n=len(lst), parts=plist)
            desc = self.fit(base, [t("seo.desc.municipalityPad")], self.en["seo"]["desc"]["tail"])
            bl = [{"@type": "ListItem", "position": 1, "name": t("crumb.home"), "item": self.canon("")},
                  {"@type": "ListItem", "position": 2, "name": t("muni.crumbList"), "item": self.canon("municipalities/")},
                  {"@type": "ListItem", "position": 3, "name": mun, "item": self.canon(rel)}]
            page = {"rel": rel, "view": "static", "tab": None, "title": title, "desc": desc,
                    "jsonld": [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": bl}],
                    "slots": {"static": "".join(o)}}
            self.write(rel, self.page(page))
            self.sitemap["municipalities"].append(rel)

    # ------------------------------------------------------------ misc files
    def write_text(self, rel, txt):
        p = self.out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf8", newline="\n")

    def sitemaps(self):
        def urlset(rels, lastmod):
            u = "".join(f"<url><loc>{e(self.canon(r))}</loc><lastmod>{lastmod}</lastmod></url>" for r in rels)
            return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + u + "</urlset>\n"

        self.write_text("sitemap-pages.xml", urlset(self.sitemap["pages"], self.site_lastmod))
        self.write_text("sitemap-schools.xml", urlset(self.sitemap["schools"], self.generated))
        self.write_text("sitemap-municipalities.xml", urlset(self.sitemap["municipalities"], self.generated))
        idx = "".join(f"<sitemap><loc>{e(self.site_url + '/' + n)}</loc><lastmod>{lm}</lastmod></sitemap>" for n, lm in [("sitemap-pages.xml", self.site_lastmod), ("sitemap-schools.xml", self.generated), ("sitemap-municipalities.xml", self.generated)])
        self.write_text("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + idx + "</sitemapindex>\n")
        robots = "User-agent: *\nAllow: /\n"
        if self.indexable:
            robots += f"\nSitemap: {self.site_url}/sitemap.xml\n"
        self.write_text("robots.txt", robots)

    def favicon_ico(self):
        """32x32 route-line mark as a PNG inside an .ico (stdlib only)"""
        n = 32
        navy, yel, clear_ = (0, 48, 130, 255), (255, 201, 23, 255), (0, 0, 0, 0)
        px = [[clear_] * n for _ in range(n)]
        sc = n / 28.0

        def fill(x0, y0, x1, y1, col):
            for y in range(max(0, int(round(y0 * sc))), min(n, int(round(y1 * sc)))):
                for x in range(max(0, int(round(x0 * sc))), min(n, int(round(x1 * sc)))):
                    px[y][x] = col

        fill(11, 0, 17, 28, navy)
        for y in (3, 11, 19):
            fill(5 - 1.5, y - 1.5, 23 + 1.5, y + 6 + 1.5, navy)
            fill(5 + 1.5, y + 1.5, 23 - 1.5, y + 6 - 1.5, yel)
        raw = b"".join(b"\x00" + b"".join(bytes(c) for c in row) for row in px)

        def chunk(tp, data):
            c = struct.pack(">I", len(data)) + tp + data
            return c + struct.pack(">I", zlib.crc32(tp + data) & 0xFFFFFFFF)

        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
        ico = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", n, n, 0, 0, 1, 32, len(png), 22) + png
        (self.out / "favicon.ico").write_bytes(ico)

    # ------------------------------------------------------------ main
    def run(self):
        t = self.t
        out = self.out
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        # assets
        for f in ("app.js", "app.css", "og.png", "favicon.svg"):
            shutil.copy2(SITE / f, out / f)
        (out / "i18n").mkdir()
        for f in (SITE / "i18n").glob("*.json"):
            shutil.copy2(f, out / "i18n" / f.name)
        (out / "data").mkdir()
        for f in DATA.glob("*.json"):
            shutil.copy2(f, out / "data" / f.name)
        (out / ".nojekyll").write_text("", encoding="utf8")
        if (SITE / "CNAME").is_file():
            shutil.copy2(SITE / "CNAME", out / "CNAME")
        self.favicon_ico()

        # municipalities
        by_mun = {}
        for s in self.schools:
            if s["mun"]:
                by_mun.setdefault(s["mun"], []).append(s)
        self.mslug = {}
        seen = {}
        for mun in sorted(by_mun):
            sl = slugify(mun)
            assert sl and sl not in seen, ("municipality slug clash", mun, seen.get(sl))
            seen[sl] = mun
            self.mslug[mun] = sl
        tops = self.province_tops()
        assert len(tops) == 12, tops

        D = self.en["seo"]["desc"]

        def simple(rel, view, title_key, desc, slots=None, jsonld=None, **kw):
            page = {"rel": rel, "view": view, "title": t(title_key), "desc": desc, "jsonld": jsonld or [], "slots": slots or {}}
            page.update(kw)
            self.write(rel, self.page(page))
            if kw.get("index", True) and kw.get("sitemap", True):
                self.sitemap["pages"].append(rel)

        # home
        how = (f'<h3>{e(t("home.howTitle"))}</h3><ol><li>{e(t("home.how1"))}</li><li>{e(t("home.how2"))}</li><li>{e(t("home.how3"))}</li></ol>')
        ws = {"@context": "https://schema.org", "@type": "WebSite", "name": self.brand, "url": self.canon(""), "inLanguage": self.langs[0], "description": t("meta.description")}
        simple("", "route", "title.route", t("meta.description"), {"homelinks": how + self.home_links(tops)}, [ws], tab="route")
        simple("find/", "find", "title.find", D["find"], {"findout": f'<noscript><p class="note">{e(t("findStatic.noscript"))}</p></noscript><p><a href="{self.href("municipalities/")}">{e(t("home.linksAll"))}</a></p>'}, tab="find")
        simple("map/", "map", "title.map", D["map"], {"mapout": f'<noscript><p class="note">{e(t("mapStatic.noscript"))}</p></noscript><p><a href="{self.href("municipalities/")}">{e(t("home.linksAll"))}</a></p>'}, tab="map")
        simple("system/", "system", "title.system", D["system"], self.system_slots(), tab="system")
        simple("questions/", "faq", "title.faq", D["faq"], {"faq": self.faq_html()}, [self.faq_jsonld()], tab="faq")
        simple("sources/", "sources", "title.sources", D["sources"], {"sourcesout": self.sources_html()}, tab="sources")
        # compare: client side, never indexed
        simple("compare/", "compare", "title.compare", D["compare"], {"compareout": f'<p>{e(t("compareStatic.text"))}</p><noscript><p class="note">{e(t("compareStatic.noscript"))}</p></noscript><p><a href="{self.href("find/")}">{e(t("home.linksFind"))}</a></p>'}, tab="find", index=False, sitemap=False)

        # municipalities index
        provs = {}
        for mun, lst in by_mun.items():
            pv = max(set(s["provN"] for s in lst), key=lambda p: sum(1 for s in lst if s["provN"] == p))
            provs.setdefault(pv, []).append((mun, len(lst)))
        o = [f'<div class="phead">{self.crumbs([(t("crumb.home"), self.href("")), (t("munis.h1"), None)])}<h1 class="vh" id="h-static" tabindex="-1">{e(t("munis.h1"))}</h1><p>{e(t("munis.intro", n=len(by_mun)))}</p></div>']
        for pv in sorted(provs):
            li = "".join(f'<li><a href="{self.href("municipality/" + self.mslug[m] + "/")}">{e(m)}</a> <span class="note">({e(t("munis.count", n=n))})</span></li>' for m, n in sorted(provs[pv], key=lambda x: x[0].lower()))
            o.append(f'<section class="psec azgrp"><h2>{e(pv)}</h2><ul class="az">{li}</ul></section>')
        pg = {"rel": "municipalities/", "view": "static", "tab": None, "title": t("title.municipalities"), "desc": D["municipalities"],
              "jsonld": [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": t("crumb.home"), "item": self.canon("")}, {"@type": "ListItem", "position": 2, "name": t("munis.h1"), "item": self.canon("municipalities/")}]}],
              "slots": {"static": "".join(o)}}
        self.write("municipalities/", self.page(pg))
        self.sitemap["pages"].append("municipalities/")

        # 404
        nf_html = (f'<div class="phead nf404"><h1 class="vh" id="h-static" tabindex="-1">{e(t("notfound.h1"))}</h1><p>{e(t("notfound.text"))}</p>'
                   f'<p id="nf-lookup">{e(t("notfound.lookup"))}</p><ul>'
                   f'<li><a href="{self.href("find/")}">{e(t("notfound.tryFind"))}</a></li><li><a href="{self.href("")}">{e(t("notfound.tryHome"))}</a></li><li><a href="{self.href("system/")}">{e(t("notfound.trySystem"))}</a></li></ul></div>')
        pg = {"rel": "404.html", "view": "static", "tab": None, "title": t("title.notFound"), "desc": D["notFound"], "canonical": False, "index": False, "jsonld": [], "slots": {"static": nf_html}}
        s404 = self.page(pg)
        self.write_text("404.html", s404)
        self.pages += 1

        # municipality pages, schools
        self.muni_pages(by_mun)
        near = nearest_same_type(self.schools)
        for s in self.schools:
            p = self.school_page(s, near.get(s["id"], []))
            self.write(p["rel"], self.page(p))
            self.sitemap["schools"].append(p["rel"])
        self.sitemaps()
        return self.pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "_site"))
    ap.add_argument("--seo", default=str(SITE / "seo.json"))
    a = ap.parse_args()
    b = Build(a.out, a.seo)
    n = b.run()
    total = sum(f.stat().st_size for f in Path(a.out).rglob("*") if f.is_file())
    print(f"pages: {n}  (schools {len(b.sitemap['schools'])}, municipalities {len(b.sitemap['municipalities'])}, other {len(b.sitemap['pages'])} indexable + compare + 404)")
    print(f"_site size: {total / 1e6:.1f} MB   indexable: {b.indexable}")


if __name__ == "__main__":
    main()
