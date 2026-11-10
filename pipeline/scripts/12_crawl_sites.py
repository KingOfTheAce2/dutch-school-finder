"""Step 2 of the feature enrichment: polite crawl of school websites for feature flags and open-day dates.

Unit of work = one website host (many DUO locations share a host). One JSONL line per finished host is
appended to the checkpoint with flush + fsync; on restart finished hosts are skipped (resumable).

Politeness: identified User-Agent, robots.txt obeyed (also Crawl-delay, capped), >= 1 s between requests per
registrable domain, a handful of hosts in parallel, homepage + at most 5 internal pages chosen by keyword.
Only facts are stored: feature flags and open-day dates, each with the source URL and a short (<=150 chars)
evidence snippet. No page text or images are kept. Every fetched page is untrusted data: it is parsed with
bs4/regex only, never executed, and nothing in it is treated as an instruction.

Run with `python -I` (needs beautifulsoup4 + lxml):
  python -I scripts/12_crawl_sites.py --limit 20 --seed 1 --checkpoint raw/crawl_test.jsonl   # test batch
  python -I scripts/12_crawl_sites.py --workers 8                                              # full run, resumable
"""
import os, sys, re, json, time, zlib, random, argparse, datetime, threading, socket, ssl
import urllib.request, urllib.error, urllib.parse, urllib.robotparser
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, OUT, JsonlAppender, read_jsonl
from bs4 import BeautifulSoup

UA = "SchoollijnBot/0.1 (research; contact via site)"
ROBOT_TOKEN = "SchoollijnBot"
TODAY = datetime.date.today()
MAX_PAGES = 5            # internal pages besides the homepage
MAX_BYTES = 2_000_000
TIMEOUT = 15
GAP = 1.0                # seconds between requests to one registrable domain
CRAWL_DELAY_CAP = 10.0

# ----------------------------------------------------------------------------------------------
# politeness gate (per registrable domain)
_last, _lk = {}, threading.Lock()


def regdom(h):
    p = (h or "").split(".")
    return ".".join(p[-2:]) if len(p) >= 2 else (h or "")


def gate(key, gap):
    with _lk:
        now = time.monotonic()
        slot = max(now, _last.get(key, 0.0) + gap)
        _last[key] = slot
    d = slot - now
    if d > 0:
        time.sleep(d)


# ----------------------------------------------------------------------------------------------
class Site:
    """Per-host fetch state: robots.txt cache, crawl delay."""

    def __init__(self):
        self.robots = {}   # host -> (RobotFileParser|None, delay, blocked_all)

    def _load_robots(self, scheme, host):
        key = host
        if key in self.robots:
            return self.robots[key]
        rp = urllib.robotparser.RobotFileParser()
        res = (None, GAP, False)
        try:
            gate(regdom(host), GAP)
            req = urllib.request.Request("%s://%s/robots.txt" % (scheme, host), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read(300_000).decode("utf-8", "replace")
            rp.parse(body.splitlines())
            cd = rp.crawl_delay(ROBOT_TOKEN) or rp.crawl_delay("*")
            res = (rp, max(GAP, min(float(cd), CRAWL_DELAY_CAP)) if cd else GAP, False)
            if cd and float(cd) > CRAWL_DELAY_CAP:
                res = (rp, CRAWL_DELAY_CAP, False)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403) or e.code >= 500:
                res = (None, GAP, True)      # treat as disallow-all (conservative)
            else:
                res = (None, GAP, False)     # 404 etc.: no robots.txt = allowed
        except Exception:
            res = (None, GAP, False)         # unreachable robots: the page fetch will report the real error
        self.robots[key] = res
        return res

    def allowed(self, url):
        u = urllib.parse.urlsplit(url)
        rp, delay, blocked = self._load_robots(u.scheme, u.hostname)
        if blocked:
            return False, delay
        if rp is None:
            return True, delay
        return rp.can_fetch(ROBOT_TOKEN, url), delay


# ----------------------------------------------------------------------------------------------
BAD_EXT = re.compile(r"\.(pdf|jpe?g|png|gif|webp|svg|zip|docx?|xlsx?|pptx?|mp[34]|avi|mov|ico|css|js|xml|rss)(\?|$)", re.I)


def fetch(url, site):
    """Return (final_url, text, soup) or raise. Obeys robots (before and after redirects)."""
    ok, delay = site.allowed(url)
    if not ok:
        raise PermissionError("robots")
    gate(regdom(urllib.parse.urlsplit(url).hostname), delay)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
                                               "Accept-Language": "nl,en;q=0.7", "Accept-Encoding": "gzip, identity"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        final = r.geturl()
        ctype = r.headers.get_content_type()
        if ctype not in ("text/html", "application/xhtml+xml", "text/plain"):
            raise ValueError("content-type " + ctype)
        raw = r.read(MAX_BYTES)
        if (r.headers.get("Content-Encoding") or "").lower() == "gzip":
            raw = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw, MAX_BYTES)
        cs = r.headers.get_content_charset()
    if final != url:
        fh = urllib.parse.urlsplit(final).hostname
        if fh != urllib.parse.urlsplit(url).hostname:
            ok2, _ = site.allowed(final)
            if not ok2:
                raise PermissionError("robots(redirect)")
    text = None
    for enc in [cs, "utf-8", "cp1252"]:
        if not enc:
            continue
        try:
            text = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if text is None:
        text = raw.decode("utf-8", "replace")
    return final, text


# ----------------------------------------------------------------------------------------------
# link scoring
LINK_KW = [  # (regex on lowercased "anchor text + url path", weight)
    (re.compile(r"open[ -]?(dag|avond|middag|huis)|opendag|open day|open evening"), 6),
    (re.compile(r"kennismak"), 5),
    (re.compile(r"tweetalig|bilingual|(?<![a-z0-9])tto(?![a-z0-9])"), 5),
    (re.compile(r"international baccalaureate|(?<![a-z0-9])ib[- ]?(dp|myp|pyp|diploma|world)|(?<![a-z0-9])ib(?![a-z0-9]) ?(school|onderwijs)?$"), 4),
    (re.compile(r"technasium|montessori|dalton|jenaplan|vrijeschool|vrije school|steiner|waldorf"), 4),
    (re.compile(r"gymnasium"), 3),
    (re.compile(r"(?<![a-z0-9])isk(?![a-z0-9])|schakelklas|taalklas|kopklas|nieuwkomer|newcomer|internationale|igbo|igvo|international"), 4),
    (re.compile(r"aanmeld|inschrijv|toelating"), 2),
    (re.compile(r"ons-onderwijs|onderwijs|over-ons|visie|profiel|onderwijsaanbod"), 1),
]


def pick_links(soup, base_url, host_key):
    cands = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        u = urllib.parse.urljoin(base_url, href)
        sp = urllib.parse.urlsplit(u)
        if sp.scheme not in ("http", "https") or not sp.hostname:
            continue
        if re.sub(r"^www\.", "", sp.hostname.lower()) != host_key:
            continue
        if BAD_EXT.search(sp.path) or len(u) > 160:
            continue
        u = urllib.parse.urlunsplit((sp.scheme, sp.netloc, sp.path, sp.query if len(sp.query) < 40 else "", ""))
        label = re.sub(r"\s+", " ", a.get_text(" ", strip=True))[:100].lower()
        hay = (label + " " + urllib.parse.unquote(sp.path).lower().replace("_", "-"))
        score = sum(w for rx, w in LINK_KW[:-1] if rx.search(hay))
        if score >= 2:
            score += 0
        if score <= 0:
            continue
        old = cands.get(u)
        if old is None or score > old[0]:
            cands[u] = (score, len(sp.path))
    ranked = sorted(cands.items(), key=lambda kv: (-kv[1][0], kv[1][1]))
    return [u for u, _ in ranked][:MAX_PAGES]


# ----------------------------------------------------------------------------------------------
# flag patterns. (regex, flags); matched on page text; a match preceded by a negation within 40 chars is dropped.
I = re.IGNORECASE
FLAG_RX = {
    "tto": re.compile(r"(?<![A-Za-z0-9])TTO(?![A-Za-z0-9])|tweetalig(?:e)?\s+(?:onderwijs|vwo|havo|mavo|vmbo|gymnasium|atheneum|stroom|opleiding|afdeling|leerlingen|lyceum)|bilingual\s+(?:education|stream|programme|program|school|vwo|havo)|(?<![a-z])tweetalig\b", I),
    "ib": re.compile(r"international\s+baccalaureate|IB\s+World\s+School|(?<![A-Za-z0-9])IB[\s-]?(?:DP|MYP|PYP|CP|diploma|programma|programme|program|onderwijs|stroom|afdeling)(?![A-Za-z0-9])|(?<![A-Za-z0-9])IBO(?![A-Za-z0-9])", I),
    "technasium": re.compile(r"\btechnasium", I),
    "montessori": re.compile(r"\bmontessori", I),
    "dalton": re.compile(r"\bdalton(?!\s+college)", I),
    "jenaplan": re.compile(r"\bjenaplan", I),
    "vrije_school": re.compile(r"(?<![A-Za-z])vrije\s?school(?!keuze)|(?<![A-Za-z])vrijeschool|\bwaldorf|\bsteiner(?:school|onderwijs|pedagogie)|antroposof", I),
    "international": re.compile(r"(?<![A-Za-z0-9])(?:IGBO|IGVO)(?![A-Za-z0-9])|international\s+(?:department|stream|section|class|primary|secondary|programme|program)|internationale\s+(?:afdeling|stroom|klas|sectie|basisschool)|english[- ]medium", I),
    "newcomer": re.compile(r"(?<![A-Za-z0-9])ISK(?![A-Za-z0-9])|internationale\s+schakelklas|taalklas|kopklas|nieuwkomers?(?:klas|onderwijs|groep|school|afdeling|leerlingen|\b)|newcomers?\s+(?:class|education|school|programme)|eerste\s+opvang\s+anderstaligen|(?<![A-Za-z0-9])EOA(?![A-Za-z0-9])|schakelklas(?=[^.]{0,80}(?:nieuwkomer|anderstalig|taal))|(?<=anderstalige )schakelklas|(?<=nieuwkomers )schakelklas", I),
}
# need case-sensitive handling for short acronyms: re-verify after a match
ACRONYM = {"tto": "TTO", "ib": None, "newcomer": None}
NEG = re.compile(r"(?:\bgeen\b|\bniet\b|\bzonder\b|\bnot\b|\bno\b|\bnog niet\b)[^.]{0,30}$", I)


def clean_text(soup):
    for t in soup(["script", "style", "noscript", "template", "svg", "iframe"]):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:400_000]


def snippet(text, m, width=150):
    a = max(0, m.start() - 55)
    s = text[a:a + width]
    return re.sub(r"\s+", " ", s).strip()


def count_matches(flag, rx, text):
    """Matches of one flag regex in text, ignoring wrong-case acronyms and negated mentions. -> (n, first_match_or_None)"""
    n, first = 0, None
    for m in rx.finditer(text):
        tok = m.group(0)
        if flag == "tto" and tok.upper() == "TTO" and tok != "TTO":
            continue
        if flag == "ib" and tok.upper() in ("IBO",) and tok != "IBO":
            continue
        if flag == "newcomer" and tok.upper() in ("ISK", "EOA") and tok != tok.upper():
            continue
        if NEG.search(text[max(0, m.start() - 45):m.start()]):
            continue
        n += 1
        if first is None:
            first = m
    return n, first


def find_flags(text_full, text_body, text_anchors, heading_signals):
    """-> {flag: {'n': body matches, 'na': menu/link matches, 'strong': term in title/heading/url, 'snip': str}} for one page.
    text_body = page text without link text; text_anchors = link texts joined by ' | '."""
    out = {}
    for flag, rx in FLAG_RX.items():
        n, m_body = count_matches(flag, rx, text_body)
        na, m_anc = count_matches(flag, rx, text_anchors)
        strong = bool(rx.search(heading_signals))
        if not (n or na or strong):
            continue
        snip = None
        if m_body:
            snip = snippet(text_body, m_body)
        else:
            m_full = rx.search(text_full)
            if m_full:
                snip = snippet(text_full, m_full)
        out[flag] = {"n": n, "na": na, "strong": strong, "snip": snip}
    return out


# ---------------------------------------------------------------------------------------------- dates
MONTHS = {"januari": 1, "jan": 1, "february": 2, "februari": 2, "feb": 2, "maart": 3, "mrt": 3, "march": 3, "april": 4, "apr": 4,
          "mei": 5, "may": 5, "juni": 6, "jun": 6, "june": 6, "juli": 7, "jul": 7, "july": 7, "augustus": 8, "aug": 8, "august": 8,
          "september": 9, "sept": 9, "sep": 9, "oktober": 10, "okt": 10, "october": 10, "oct": 10, "november": 11, "nov": 11,
          "december": 12, "dec": 12, "january": 1}
MON_RX = "|".join(sorted(MONTHS, key=len, reverse=True))
DATE_TXT = re.compile(r"(?<!\d)(\d{1,2})(?:\s*(?:en|&|,|/|t/m|tot|-)\s*(\d{1,2}))?\s*(?:e\s)?(" + MON_RX + r")\.?(?:\s*,?\s*(20\d{2}))?(?!\w)", I)
DATE_ENG = re.compile(r"\b(" + MON_RX + r")\.?\s+(\d{1,2})(?:(?:st|nd|rd|th)\b|,?\s*(20\d{2}))", I)
DATE_NUM = re.compile(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2}|\d{2})(?!\d)")
OPEN_RX = re.compile(r"open[ -]?(?:dag|avond|middag|huis|ochtend)|opendag|openhuis|kennismakings?[ -]?(?:dag|middag|avond|ochtend|bijeenkomst|les|morgen)|kennismaking|open (?:day|evening|house)|informatie[ -]?(?:avond|dag)|infoavond|infodag|inloopavond|inloopdag|voorlichtings?[ -]?(?:avond|dag|middag)", I)
LABELS = [(re.compile(r"open[ -]?avond|open evening", I), "Open avond"),
          (re.compile(r"open[ -]?middag", I), "Open middag"),
          (re.compile(r"open[ -]?huis|openhuis|open house", I), "Open huis"),
          (re.compile(r"kennismak", I), "Kennismaking"),
          (re.compile(r"informatie[ -]?(?:avond|dag)|infoavond|infodag|inloop|voorlichting", I), "Informatieavond/-dag"),
          (re.compile(r"open[ -]?dag|opendag|open day|open ochtend", I), "Open dag")]
WEEKDAYS = {"maandag": 0, "dinsdag": 1, "woensdag": 2, "donderdag": 3, "vrijdag": 4, "zaterdag": 5, "zondag": 6,
            "ma": 0, "di": 1, "wo": 2, "do": 3, "vr": 4, "za": 5, "zo": 6}
WD_RX = re.compile(r"(?<![A-Za-z])(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag|ma|di|wo|do|vr|za|zo)\.?,?\s*$", I)
STOP_EVENT = re.compile(r"studiedag|vakantie|ouderavond|meeloop|proefles|proefdag|toets|examen|cito|ouderbijdrage|schoolreis|\bkamp\b|sportdag|vrije dag|margedag", re.I)
YEAR_RX = re.compile(r"(?<!\d)(20[12]\d)(?!\d)")


def school_year(d):
    y = d.year if d.month >= 8 else d.year - 1
    return "%d/%02d" % (y, (y + 1) % 100)


def resolve_date(day, mon, year, weekday):
    """-> (date|None, inferred). A weekday written before the date must agree with the calendar; when the year is
    missing, the candidate years (this year, next year) are tried and the one that agrees is used."""
    if year is not None:
        try:
            d = datetime.date(year, mon, day)
        except ValueError:
            return None, False
        if weekday is not None and d.weekday() != weekday:
            return None, False
        return d, False
    for y in (TODAY.year, TODAY.year + 1):
        try:
            d = datetime.date(y, mon, day)
        except ValueError:
            continue
        if d < TODAY:
            continue
        if weekday is not None and d.weekday() != weekday:
            continue
        return d, True
    return None, True


def find_open_days(text):
    """Dates tied to an open-day keyword. Each date mention is attached to the nearest preceding keyword (<=170 chars,
    no unrelated event word in between), else to a keyword right after it (<=30 chars). -> list of dicts."""
    kws = [(m.start(), m.end(), next((lb for rx, lb in LABELS if rx.search(m.group(0))), "Open dag")) for m in OPEN_RX.finditer(text)]
    if not kws:
        return []
    mentions = []   # (pos, day, mon, year, end_pos)
    for m in DATE_TXT.finditer(text):
        mon = MONTHS.get(m.group(3).lower())
        if not mon:
            continue
        d1, d2, yr = m.group(1), m.group(2), m.group(4)
        days = [int(d1)]
        if d2 and re.search(r"en|&|,", text[m.start(1):m.start(3)], re.I):
            days.append(int(d2))
        for dd in days:
            mentions.append((m.start(), dd, mon, int(yr) if yr else None, m.end()))
    for m in DATE_ENG.finditer(text):
        mon = MONTHS.get(m.group(1).lower())
        if mon:
            mentions.append((m.start(), int(m.group(2)), mon, int(m.group(3)) if m.group(3) else None, m.end()))
    for m in DATE_NUM.finditer(text):
        yy = int(m.group(3))
        mentions.append((m.start(), int(m.group(1)), int(m.group(2)), yy + 2000 if yy < 100 else yy, m.end()))
    res = {}
    for pos, dd, mon, yr, end in mentions:
        if not (1 <= dd <= 31 and 1 <= mon <= 12):
            continue
        label = None
        for ks, ke, lb in reversed(kws):         # nearest preceding keyword
            if ke <= pos + 2 and pos - ke <= 170 and ks < pos:
                between = text[ke:pos]
                if not STOP_EVENT.search(between):
                    label = lb
                break
        if label is None:
            nxt = min([q[0] for q in mentions if q[0] > pos] or [10 ** 9])
            for ks, ke, lb in kws:               # keyword right after the date ("12 november Open avond")
                if ks >= end and ks - end <= 15 and ks < nxt:
                    label = lb
                    break
        if label is None:
            continue
        wm = WD_RX.search(text[max(0, pos - 14):pos])
        wd = WEEKDAYS.get(wm.group(1).lower()) if wm else None
        d, inf = resolve_date(dd, mon, yr, wd)
        if not d or d < TODAY or d > datetime.date(TODAY.year + 1, 8, 31):
            continue
        ctx = text[max(0, pos - 26):end + 12]
        if any(int(y) != d.year and int(y) < TODAY.year for y in YEAR_RX.findall(ctx)):
            continue                              # stale news item ("Open dag 2024 vrijdag 19 januari")
        if inf and label == "Kennismaking" and wd is None:
            continue                              # kennismaking dates without year or weekday are too often generic
        key = (d.isoformat(), label)
        if key not in res:
            res[key] = {"date": d.isoformat(), "label": label, "school_year": school_year(d), "inferred": inf}
    return list(res.values())



# ---------------------------------------------------------------------------------------------- one host
def crawl_host(unit_key, home_url, ids, site):
    host_key = unit_key
    host_key = host_key.split("/")[0]
    unit = unit_key
    rec = {"host": unit, "ids": ids, "home": home_url, "checked": TODAY.isoformat(), "status": "ok", "pages": [], "errors": []}
    t0 = time.time()
    try:
        final, html = None, None
        tried = []
        for u in ([home_url] if home_url.startswith("http://") else [home_url, "http://" + home_url[len("https://"):]]):
            try:
                final, html = fetch(u, site)
                break
            except PermissionError as e:
                raise
            except (ssl.SSLError, urllib.error.URLError, socket.timeout, ConnectionError, OSError, ValueError) as e:
                tried.append("%s: %s" % (u[:8], str(getattr(e, "reason", e))[:60]))
                if isinstance(e, urllib.error.HTTPError):
                    raise
                continue
        if html is None:
            rec["status"] = "error"
            rec["errors"].append("home: " + "; ".join(tried))
            return rec
        fhost = re.sub(r"^www\.", "", urllib.parse.urlsplit(final).hostname.lower())
        if regdom(fhost) != regdom(host_key):
            rec["redirect_offsite"] = fhost
        pages = [(final, html)]
        soup0 = BeautifulSoup(html, "lxml")
        links = pick_links(soup0, final, fhost)
        for l in links:
            try:
                f2, h2 = fetch(l, site)
                pages.append((f2, h2))
            except PermissionError:
                rec["errors"].append("robots: " + l[-60:])
            except urllib.error.HTTPError as e:
                rec["errors"].append("%s %s" % (e.code, l[-60:]))
            except Exception as e:
                rec["errors"].append("%s %s" % (type(e).__name__, l[-60:]))
        flags, days = {}, {}
        for url, h in pages:
            soup = BeautifulSoup(h, "lxml")
            title = (soup.title.get_text(" ", strip=True) if soup.title else "")
            heads = " ".join(x.get_text(" ", strip=True) for x in soup.find_all(["h1", "h2", "h3"])[:15])
            path = urllib.parse.unquote(urllib.parse.urlsplit(url).path).replace("-", " ").replace("_", " ")
            for t in soup(["script", "style", "noscript", "template", "svg", "iframe"]):
                t.decompose()
            text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:400_000]       # with link text (open days, snippets)
            alist = [re.sub(r"\s+", " ", a.get_text(" ", strip=True))[:80] for a in soup.find_all("a")[:400]]
            anchors = " | ".join(x for x in alist if x)
            for a in soup.find_all("a"):
                a.decompose()
            body = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:400_000]       # without link text
            pf = find_flags(text, body, anchors, " ".join([title, heads, path]))
            rec["pages"].append(url)
            for fl, v in pf.items():
                cur = flags.setdefault(fl, {"n": 0, "na": 0, "strong": False, "url": None, "snip": None})
                cur["n"] += v["n"]
                cur["na"] += v["na"]
                if v["snip"] and (cur["snip"] is None or (v["n"] and not cur.get("body"))):
                    cur["snip"], cur["url"] = v["snip"], url
                    cur["body"] = bool(v["n"])
                cur["strong"] = cur["strong"] or v["strong"]
                if cur["url"] is None:
                    cur["url"] = url
            yrs = {int(y) for y in re.findall(r"(?<!\d)(20\d\d)(?!\d)", urllib.parse.unquote(urllib.parse.urlsplit(url).path))}
            stale = any(y < TODAY.year for y in yrs)
            for d in ([] if stale else find_open_days(text)):
                k = (d["date"], d["label"])
                if k not in days:
                    days[k] = dict(d, url=url)
        keep = {}
        for fl, v in flags.items():     # raw counts are stored; 13_build_features.py applies the acceptance rules
            keep[fl] = {"url": v["url"], "snip": (v["snip"] or "")[:150], "n": v["n"], "na": v["na"], "strong": v["strong"]}
        rec["flags"] = keep
        rec["open_days"] = sorted(days.values(), key=lambda x: x["date"])
    except PermissionError:
        rec["status"] = "robots_disallow"
    except urllib.error.HTTPError as e:
        rec["status"] = "error"
        rec["errors"].append("home HTTP %s" % e.code)
    except Exception as e:
        rec["status"] = "error"
        rec["errors"].append("%s: %s" % (type(e).__name__, str(e)[:80]))
    rec["secs"] = round(time.time() - t0, 1)
    return rec


# ---------------------------------------------------------------------------------------------- target list
PO_RX = re.compile(r"montessori|dalton|jenaplan|vrije\s?school|vrijeschool|waldorf|steiner|international|internationa|igbo|english|bilingual|tweetalig|"
                   r"(?<![a-z])isk(?![a-z])|nieuwkomer|newcomer|taalschool|taalklas|schakel|kopklas|expat|\bibo?\b|\bib\b", re.I)


def load_targets(po_all=False):
    targets = {}   # host -> {"home":..., "ids":[...]}

    first_url = {}

    def add(sid, web):
        if not web:
            return
        h = re.sub(r"^www\.", "", web.strip().lower().split("/")[0])
        if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", h):
            return
        norm = re.sub(r"^www\.", "", web.strip().lower().rstrip("/"))
        # unit key: the host for the first URL seen on that host; host + path for other URLs on the same host
        # (e.g. one school group with a sub-path per school), so that flags are not attributed to sibling schools
        f = first_url.setdefault(h, norm)
        key = h if norm == f else norm
        t = targets.setdefault(key, {"home": "https://" + web.strip(), "ids": []})
        t["ids"].append(sid)

    vo = json.load(open(os.path.join(OUT, "schools_vo.json"), encoding="utf-8"))
    c = {k: i for i, k in enumerate(vo["cols"])}
    for r in vo["rows"]:
        add(r[c["id"]], r[c["web"]])
    n_vo = len(targets)
    po = json.load(open(os.path.join(OUT, "schools_po.json"), encoding="utf-8"))
    c = {k: i for i, k in enumerate(po["cols"])}
    for r in po["rows"]:
        if po_all or PO_RX.search(r[c["name"]] or "") or PO_RX.search(r[c["web"]] or ""):
            add(r[c["id"]], r[c["web"]])
    # PO schools found on association lists (international, concept) are crawled too
    mp = os.path.join(RAW, "list_matches.json")
    if os.path.exists(mp):
        lm = json.load(open(mp, encoding="utf-8"))["matched"]
        for sid, L in lm.items():
            if sid[:2].isdigit() and any(m["match"].get("pool") == "po" for m in L):
                pass
        wp = {r[c["id"]]: r[c["web"]] for r in po["rows"]}
        for sid, L in lm.items():
            if sid in wp and any(m["source"] in ("dis", "sio") for m in L):
                add(sid, wp[sid])
    return targets, n_vo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default=os.path.join(RAW, "crawl_checkpoint.jsonl"))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--po-all", action="store_true")
    ap.add_argument("--hosts", default="", help="comma separated hosts (test runs)")
    a = ap.parse_args()
    targets, n_vo = load_targets(a.po_all)
    hosts = sorted(targets)
    if a.hosts:
        hosts = [h for h in a.hosts.split(",") if h in targets]
    if a.limit:
        random.Random(a.seed).shuffle(hosts)
        hosts = hosts[:a.limit]
    done = {r["host"] for r in read_jsonl(a.checkpoint)}
    todo = [h for h in hosts if h not in done]
    print("targets %d hosts (%d from VO); done %d; todo %d" % (len(targets), n_vo, len(done), len(todo)), flush=True)
    app = JsonlAppender(a.checkpoint)
    site = Site()
    lock = threading.Lock()
    n = 0
    t0 = time.time()
    # work in small waves so a kill loses at most the in-flight hosts
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {}
        it = iter(todo)

        def submit():
            try:
                h = next(it)
            except StopIteration:
                return False
            futs[ex.submit(crawl_host, h, targets[h]["home"], targets[h]["ids"], site)] = h
            return True

        for _ in range(a.workers):
            submit()
        while futs:
            done_f, _ = cf.wait(list(futs), return_when=cf.FIRST_COMPLETED)
            for f in done_f:
                h = futs.pop(f)
                try:
                    rec = f.result()
                except Exception as e:
                    rec = {"host": h, "ids": targets[h]["ids"], "home": targets[h]["home"], "checked": TODAY.isoformat(),
                           "status": "error", "errors": ["crash " + type(e).__name__ + str(e)[:60]], "pages": []}
                app.write(rec)
                n += 1
                if n % 25 == 0:
                    print("%d/%d hosts, %.0fs" % (n, len(todo), time.time() - t0), flush=True)
                submit()
    app.close()
    print("finished %d hosts in %.0fs" % (n, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
