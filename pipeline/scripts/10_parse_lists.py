"""Parse the authoritative association lists (snapshots saved in raw/lists/) into
raw/lists_parsed.json: {source_key: [entry, ...]}.
Entry: {name, city, pc (6 chars or None), addr, web, extra:{...}}.
Snapshots are fetched by 10_fetch_lists.py. Run with `python -I`.
All inputs are untrusted downloads: parsed with bs4/json only, never executed."""
import os, sys, re, json, glob, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW
from bs4 import BeautifulSoup

L = os.path.join(RAW, "lists")


def rd(name):
    with open(os.path.join(L, name), "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def pc6(s):
    m = re.search(r"(\d{4})\s?([A-Za-z]{2})\b", s or "")
    return (m.group(1) + m.group(2).upper()) if m else None


def parse_nuffic():
    soup = BeautifulSoup(rd("nuffic_tto_all.html"), "lxml")
    out, city = [], None
    for h in soup.select("div.field--name-field-formatted-text h3, div.field--name-field-formatted-text p"):
        if h.name == "h3":
            city = h.get_text(" ", strip=True)
            continue
        a = h.find("a")
        txt = h.get_text(" ", strip=True)
        if not city or " - " not in txt and "–" not in txt and ", t" not in txt:
            if not a:
                continue
        name = a.get_text(" ", strip=True) if a else re.split(r"\s[-–]\s", txt)[0]
        lv = re.findall(r"\bt(?:vwo|havo|vmbo|gymnasium|atheneum|mavo)\b", txt)
        out.append({"name": name, "city": city, "pc": None, "addr": None,
                    "web": a.get("href") if a else None, "extra": {"levels": lv, "raw": txt[:160]}})
    return out


def parse_technasium():
    out = []
    for f in sorted(glob.glob(os.path.join(L, "technasium_net", "*.html"))):
        net = os.path.basename(f)[:-5]
        soup = BeautifulSoup(open(f, encoding="utf-8", errors="replace").read(), "lxml")
        lines = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]
        try:
            i = lines.index("Aangesloten scholen")
        except ValueError:
            continue
        seg = []
        for l in lines[i + 1:]:
            if l.startswith("De scholen van") or l.startswith("Partners") or l.startswith("Partner"):
                break
            seg.append(l)
        j = 0
        while j < len(seg):
            if j + 1 < len(seg) and pc6(seg[j + 1]) and re.search(r"\d{4}\s?[A-Z]{2}", seg[j + 1]):
                addr = seg[j + 1]
                m = re.match(r"(.*?),\s*(\d{4}\s?[A-Z]{2})\s+(.*)", addr)
                web = seg[j + 2] if j + 2 < len(seg) and "." in seg[j + 2] and " " not in seg[j + 2] else None
                out.append({"name": seg[j], "city": m.group(3) if m else None, "pc": pc6(addr),
                            "addr": m.group(1) if m else addr, "web": web, "extra": {"network": net}})
                j += 3 if web else 2
            else:
                j += 1
    return out


def parse_wpsl(fname, extra=None):
    d = json.loads(rd(fname))
    out = []
    for s in d:
        out.append({"name": html.unescape(s.get("store", "")), "city": html.unescape(s.get("city", "") or ""),
                    "pc": pc6(s.get("zip")), "addr": html.unescape(s.get("address", "") or ""),
                    "web": s.get("url") or None, "extra": {"id": s.get("id")}})
    return out


def unesc(x):
    x = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), x)
    return html.unescape(x)


def parse_vrije():
    t = rd("vrije_onze.html").replace('\\"', '"').replace("\\\\", "\\")
    out, seen = [], set()
    for chunk in t.split('cms.vrijescholen.nl/api/collections/schools/entries/')[1:]:
        def f(k):
            m = re.search(r'"%s":"((?:[^"\\]|\\.)*)"' % k, chunk)
            return unesc(m.group(1)) if m else None
        sid = re.match(r"[0-9a-f-]{36}", chunk)
        sid = sid.group(0) if sid else None
        if not sid or sid in seen:
            continue
        seen.add(sid)
        mt = re.search(r'"status":"[^"]*",(?:"street":(?:"[^"]*"|null),)?"title":"((?:[^"\\]|\\.)*)"', chunk)
        title = unesc(mt.group(1)) if mt else None
        if not title:
            continue
        et = re.search(r'"educationType":\{[^}]*?"slug":"([^"]+)"', chunk)
        st = f("status")
        if st and st != "published":
            continue
        out.append({"name": title, "city": f("city"), "pc": pc6(f("postcode") or f("postalcode")),
                    "addr": ((f("street") or "") + " " + (f("housenumber") or "")).strip() or None,
                    "web": f("website"), "extra": {"type": et.group(1) if et else None, "id": sid}})
    return out


def parse_jenaplan():
    t = rd("jenaplan_vereniging.html")
    m = re.search(r"var init_markers = (\[.*?\]);\s*\n", t, re.S) or re.search(r"var init_markers = (\[.*?\]);", t, re.S)
    arr = json.loads(m.group(1))
    out = []
    for it in arr:
        soup = BeautifulSoup(it.get("content", ""), "lxml")
        strong = soup.find("strong")
        name = strong.get_text(" ", strip=True) if strong else None
        a = soup.find("a", href=re.compile("^http"))
        txt = [x.strip() for x in soup.get_text("\n").split("\n") if x.strip()]
        pcl = next((x for x in txt if pc6(x)), "")
        m2 = re.match(r"(\d{4}\s?[A-Z]{2})\s+(.*)", pcl)
        addr = txt[1] if len(txt) > 1 else None
        out.append({"name": name, "city": m2.group(2) if m2 else None, "pc": pc6(pcl), "addr": addr,
                    "web": a.get("href") if a else None, "extra": {"lat": it.get("lat"), "lng": it.get("lng")}})
    return out


def parse_dis():
    t = rd("dis_schools.html")
    m = re.search(r'"places":(\[.*?\]),"styles"', t, re.S)
    if not m:
        i = t.find('"places":[')
        dec = json.JSONDecoder()
        arr, _ = dec.raw_decode(t[i + len('"places":'):])
    else:
        arr = json.loads(m.group(1))
    out = []
    for p in arr:
        loc = p.get("location", {})
        cats = [c["name"] for c in p.get("categories", [])]
        out.append({"name": html.unescape(p.get("title", "")), "city": loc.get("city"), "pc": pc6(loc.get("postal_code")),
                    "addr": (p.get("address") or "").split(",")[0], "web": (loc.get("extra_fields") or {}).get("website"),
                    "extra": {"categories": cats}})
    return out


def parse_sio():
    soup = BeautifulSoup(rd("sio_city.html"), "lxml")
    out, city = [], None
    body = soup.select_one("div.entry-content") or soup
    for el in body.find_all(["p", "ul"]):
        if el.name == "p" and el.find("strong"):
            city = el.get_text(" ", strip=True)
        elif el.name == "ul" and city:
            for li in el.find_all("li"):
                a = li.find("a")
                out.append({"name": re.sub(r"\s+", " ", li.get_text(" ", strip=True).replace("\xa0", " ")), "city": city,
                            "pc": None, "addr": None, "web": a.get("href") if a else None, "extra": {}})
    return out


if __name__ == "__main__":
    res = {
        "tto": parse_nuffic(),
        "technasium": parse_technasium(),
        "montessori": parse_wpsl("montessori_ss.json"),
        "dalton": parse_wpsl("dalton_ss.json"),
        "vrije": parse_vrije(),
        "jenaplan": parse_jenaplan(),
        "dis": parse_dis(),
        "sio": parse_sio(),
    }
    for k, v in res.items():
        print(k, len(v), v[0] if v else None)
    with open(os.path.join(RAW, "lists_parsed.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False)
