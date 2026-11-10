#!/usr/bin/env python3
"""Check a built site (default _site/): links, ids, headings, tag balance, head tags, JSON-LD, sitemaps.

    python -I build/check_site.py [--site _site] [--seo site/seo.json]

Exit code 1 when anything is wrong. Stdlib only.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
ROOT = Path(__file__).resolve().parent.parent


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.hidden_depth = None
        self.ids = []
        self.hrefs = []
        self.headings = []  # (level, text) visible only
        self.errors = []
        self.meta = {}
        self.links = {}
        self.title = ""
        self._in_title = False
        self.jsonld = []
        self._in_ld = False
        self._cur_h = None
        self.landmarks = {"header": 0, "nav": 0, "main": 0, "footer": 0}
        self.imgs_no_alt = 0
        self.lang = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if tag == "img" and "alt" not in a:
            self.imgs_no_alt += 1
        if tag == "meta":
            k = a.get("name") or a.get("property")
            if k:
                self.meta.setdefault(k, []).append(a.get("content", ""))
        if tag == "link" and "rel" in a:
            self.links.setdefault(a["rel"], []).append(a)
        if tag in self.landmarks and self.hidden_depth is None:
            self.landmarks[tag] += 1
        if tag == "title":
            self._in_title = True
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True
            self.jsonld.append("")
        if tag in VOID:
            return
        self.stack.append((tag, "hidden" in a))
        if "hidden" in a and self.hidden_depth is None:
            self.hidden_depth = len(self.stack)
        if re.fullmatch(r"h[1-6]", tag) and self.hidden_depth is None:
            self._cur_h = [int(tag[1]), ""]

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._in_ld = False
        if re.fullmatch(r"h[1-6]", tag) and self._cur_h:
            self.headings.append(tuple(self._cur_h))
            self._cur_h = None
        if not self.stack or self.stack[-1][0] != tag:
            self.errors.append(f"unexpected </{tag}> (open: {self.stack[-1][0] if self.stack else None})")
            # try to recover
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break
            return
        self.stack.pop()
        if self.hidden_depth is not None and len(self.stack) < self.hidden_depth:
            self.hidden_depth = None

    def handle_data(self, d):
        if self._in_title:
            self.title += d
        if self._in_ld and self.jsonld:
            self.jsonld[-1] += d
        if self._cur_h is not None:
            self._cur_h[1] += d

    def close(self):
        super().close()
        for tag, _ in self.stack:
            self.errors.append(f"unclosed <{tag}>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=str(ROOT / "_site"))
    ap.add_argument("--sample", type=int, default=1, help="check only every Nth school page (default: all)")
    ap.add_argument("--seo", default=str(ROOT / "site" / "seo.json"))
    a = ap.parse_args()
    site = Path(a.site)
    seo = json.loads(Path(a.seo).read_text(encoding="utf8"))
    base = seo["base_path"]
    site_url = seo["site_url"].rstrip("/")
    problems = []
    n_pages = 0
    n_links = 0
    n_ld = 0
    titles = {}
    ids_by_page = {}
    pending_links = []  # (page, href)
    stats = {"noindex": 0, "desc_out": 0, "robots_bad": 0}

    files = {x.relative_to(site).as_posix() for x in site.rglob("*") if x.is_file()}

    def exists(path):
        p = unquote(path)
        if not p.startswith(base):
            return None
        rel = p[len(base):]
        if rel == "" or rel.endswith("/"):
            return rel + "index.html" in files
        return rel in files or rel + "/index.html" in files

    sc = 0
    for f in sorted(site.rglob("*.html")):
        rel = f.relative_to(site).as_posix()
        if rel.startswith("school/"):
            sc += 1
            if sc % a.sample:
                continue
        page = "/" + rel
        n_pages += 1
        p = P()
        try:
            p.feed(f.read_text(encoding="utf8"))
            p.close()
        except Exception as ex:  # noqa
            problems.append(f"{rel}: parse failure {ex}")
            continue
        for er in p.errors[:3]:
            problems.append(f"{rel}: html: {er}")
        # ids
        seen = set()
        for i in p.ids:
            if i in seen:
                problems.append(f"{rel}: duplicate id {i}")
            seen.add(i)
        ids_by_page[rel] = seen
        # headings: one visible h1, no skipped levels
        h1 = [h for h in p.headings if h[0] == 1]
        if len(h1) != 1:
            problems.append(f"{rel}: {len(h1)} visible h1")
        prev = 0
        for lvl, txt in p.headings:
            if prev and lvl > prev + 1:
                problems.append(f"{rel}: heading jump h{prev} to h{lvl} ({txt.strip()[:40]})")
                break
            prev = lvl
        for k, v in p.landmarks.items():
            if v < 1:
                problems.append(f"{rel}: no <{k}>")
        if p.lang != seo["lang"][0]:
            problems.append(f"{rel}: html lang {p.lang}")
        if p.imgs_no_alt:
            problems.append(f"{rel}: img without alt")
        # head
        t = p.title.strip()
        if not t:
            problems.append(f"{rel}: empty title")
        titles.setdefault(t, []).append(rel)
        d = (p.meta.get("description") or [""])[0]
        if rel not in ("404.html",) and not (150 <= len(d) <= 160):
            stats["desc_out"] += 1
        if not d:
            problems.append(f"{rel}: no description")
        rb = (p.meta.get("robots") or [""])[0]
        if "noindex" in rb:
            stats["noindex"] += 1
        want_noindex = (not seo["indexable"]) or rel in ("404.html", "compare/index.html")
        if want_noindex and "noindex" not in rb:
            stats["robots_bad"] += 1
            problems.append(f"{rel}: robots meta is '{rb}', expected noindex")
        if not want_noindex and rb != "index, follow":
            stats["robots_bad"] += 1
            problems.append(f"{rel}: robots meta is '{rb}', expected 'index, follow'")
        for k in ("og:title", "og:description", "og:image", "og:type", "og:site_name", "twitter:card", "viewport", "theme-color"):
            if k not in p.meta:
                problems.append(f"{rel}: missing meta {k}")
        canon = [x.get("href") for x in p.links.get("canonical", [])]
        if rel != "404.html":
            if len(canon) != 1:
                problems.append(f"{rel}: canonical count {len(canon)}")
            else:
                exp = site_url + "/" + ("" if rel == "index.html" else rel[: -len("index.html")])
                if canon[0] != exp:
                    problems.append(f"{rel}: canonical {canon[0]} != {exp}")
            alt = p.links.get("alternate", [])
            if not any(x.get("hreflang") == "x-default" for x in alt):
                problems.append(f"{rel}: no x-default hreflang")
        # json-ld
        for raw in p.jsonld:
            n_ld += 1
            try:
                j = json.loads(raw)
                if j.get("@context") != "https://schema.org" or "@type" not in j:
                    problems.append(f"{rel}: json-ld without context/type")
                if j.get("@type") in ("ElementarySchool", "HighSchool", "School") and "aggregateRating" in j:
                    problems.append(f"{rel}: aggregateRating present")
            except Exception as ex:
                problems.append(f"{rel}: json-ld invalid {ex}")
        # links
        for h in p.hrefs:
            n_links += 1
            if h.startswith("#") or h.startswith("mailto:") or h.startswith("tel:"):
                if h.startswith("#") and len(h) > 1 and h[1:] not in seen:
                    problems.append(f"{rel}: in-page anchor {h} has no target")
                continue
            u = urlsplit(h)
            if u.scheme in ("http", "https"):
                if h.startswith(site_url):
                    problems.append(f"{rel}: absolute self link {h}")
                continue
            if not u.path.startswith("/"):
                problems.append(f"{rel}: relative link {h}")
                continue
            if not u.path.startswith(base):
                problems.append(f"{rel}: link outside base {h}")
                continue
            pending_links.append((rel, u.path, u.fragment))

    # resolve links
    broken = 0
    for rel, path, frag in pending_links:
        ok = exists(path)
        if not ok:
            broken += 1
            if broken <= 15:
                problems.append(f"{rel}: broken link {path}")
            continue
        if frag:
            tgt = path[len(base):]
            tgt = (tgt + "index.html") if tgt == "" or tgt.endswith("/") else tgt
            if frag not in ids_by_page.get(tgt, set()):
                problems.append(f"{rel}: anchor #{frag} missing on {path}")
    for t, lst in titles.items():
        if len(lst) > 1 and "404.html" not in lst:
            problems.append(f"duplicate title '{t[:60]}' on {len(lst)} pages, e.g. {lst[:2]}")
    # sitemaps
    smaps = 0
    smurls = 0
    for name in ("sitemap.xml", "sitemap-pages.xml", "sitemap-schools.xml", "sitemap-municipalities.xml"):
        f = site / name
        if not f.is_file():
            problems.append(f"missing {name}")
            continue
        try:
            root = ET.fromstring(f.read_bytes())
        except ET.ParseError as ex:
            problems.append(f"{name}: invalid xml {ex}")
            continue
        smaps += 1
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for loc in root.iterfind(".//s:loc", ns):
            smurls += 1
            u = loc.text
            if not u.startswith(site_url + "/"):
                problems.append(f"{name}: {u} not under site_url")
                continue
            rel = u[len(site_url) + 1:]
            if name != "sitemap.xml":
                if not exists(base + rel):
                    problems.append(f"{name}: {u} has no page")
            elif rel not in files:
                problems.append(f"{name}: {u} missing")
    robots = (site / "robots.txt").read_text(encoding="utf8")
    has_sm = "Sitemap:" in robots
    if has_sm != bool(seo["indexable"]):
        problems.append(f"robots.txt Sitemap line {'present' if has_sm else 'absent'} but indexable={seo['indexable']}")
    if "Disallow" in robots:
        problems.append("robots.txt must not disallow while crawling is wanted")

    print(f"pages {n_pages}, links checked {n_links}, broken {broken}, json-ld blocks {n_ld}, sitemaps {smaps} ({smurls} urls)")
    print(f"noindex pages {stats['noindex']}, robots meta wrong {stats['robots_bad']}, descriptions outside 150-160: {stats['desc_out']}")
    print(f"robots.txt sitemap line: {has_sm}")
    if problems:
        print(f"{len(problems)} problems:")
        for x in problems[:60]:
            print("  ", x)
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
