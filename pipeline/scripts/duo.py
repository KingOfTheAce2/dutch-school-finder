"""Parsers for the DUO CSV files (untrusted input: stdlib csv only, everything validated)."""
import csv, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW

csv.field_size_limit(10_000_000)

PROVINCES = ["Groningen", "Friesland", "Drenthe", "Overijssel", "Flevoland", "Gelderland", "Utrecht",
             "Noord-Holland", "Zuid-Holland", "Zeeland", "Noord-Brabant", "Limburg"]

DEN_FIX = {
    "Gereformeerd vrijgemaakt / Eva": "Gereformeerd vrijgemaakt / Evangelisch",
    "Evangelische broedergemeenscha": "Evangelische broedergemeenschap",
    "Samenwerking PC, RK, Alg. Bijz": "Samenwerking PC, RK, Alg. bijzonder",
}


def read_csv(name, enc, delim=";"):
    with open(os.path.join(RAW, name), encoding=enc, newline="") as f:
        return list(csv.DictReader(f, delimiter=delim))


def norm_pc(p):
    p = re.sub(r"\s+", "", (p or "")).upper()
    return p if re.fullmatch(r"[1-9][0-9]{3}[A-Z]{2}", p) else ""


def split_hn(s):
    """'13-A' -> (13, 'A'); '4 H1' -> (4, 'H1'); '' -> (None, '')."""
    s = (s or "").strip()
    m = re.match(r"(\d+)(.*)$", s)
    if not m:
        return None, ""
    return int(m.group(1)), re.sub(r"[^A-Za-z0-9]", "", m.group(2)).upper()


URL_RE = re.compile(
    r"^(https?://)?[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}(:[0-9]{1,5})?(/[A-Za-z0-9._~%!$&()*+,;=:@/?#-]*)?$")


def clean_url(u):
    """Return a safe URL without the https:// prefix (the page adds it), or ''."""
    u = (u or "").strip()
    if not u or not URL_RE.match(u):
        return ""
    if u.lower().startswith("https://"):
        u = u[8:]
    return u


PARTICLES = {"aan", "den", "de", "het", "op", "in", "en", "ten", "ter", "te", "van", "der", "bij", "t"}


def title_nl(s):
    s = re.sub(r"\s+GEM\s+.*$", "", (s or "").strip())
    if s != s.upper() and s != s.lower():
        return s  # already mixed case
    out = []
    for i, w in enumerate(s.lower().split(" ")):
        parts = []
        for j, p in enumerate(w.split("-")):
            if p in PARTICLES and (i > 0 or j > 0):
                parts.append(p)
            elif p.startswith("'s") or p == "s":
                parts.append(p)
            elif p.startswith("'"):
                parts.append("'" + p[1:2].upper() + p[2:])
            else:
                parts.append(p[:1].upper() + p[1:])
        out.append("-".join(parts))
    return " ".join(out)


def den(s):
    s = (s or "").strip()
    return DEN_FIX.get(s, s) or "Onbekend"


def prov_idx(p):
    p = (p or "").strip()
    if p == "Fryslân":
        p = "Friesland"
    return PROVINCES.index(p) if p in PROVINCES else -1


def _school(r, id_):
    n, suf = split_hn(r["HUISNUMMER-TOEVOEGING"])
    return {
        "id": id_,
        "name": r["VESTIGINGSNAAM"].strip(),
        "street": r["STRAATNAAM"].strip(),
        "hn_raw": r["HUISNUMMER-TOEVOEGING"].strip(),
        "hn": n, "suf": suf,
        "pc6": norm_pc(r["POSTCODE"]),
        "city_raw": r["PLAATSNAAM"].strip(),
        "gemnr": r["GEMEENTENUMMER"].strip(),
        "gem_raw": r["GEMEENTENAAM"].strip(),
        "den": den(r["DENOMINATIE"]),
        "prov": prov_idx(r["PROVINCIE"]),
        "web": clean_url(r["INTERNETADRES"]),
    }


def load_po_schools():
    out = {}
    for r in read_csv("adressen_bo.csv", "cp1252"):
        s = _school(r, r["VESTIGINGSCODE"].strip())
        s["sbo"] = 0
        out[s["id"]] = s
    for r in read_csv("adressen_sbo_so_vso.csv", "cp1252"):
        if r["SOORT PRIMAIR ONDERWIJS"].strip() != "SBAO":
            continue
        s = _school(r, r["VESTIGINGSCODE"].strip())
        s["sbo"] = 1
        out[s["id"]] = s
    return list(out.values())


def load_vo_schools():
    out = []
    for r in read_csv("adressen_vo.csv", "cp1252"):
        s = _school(r, r["VESTIGINGSCODE"].strip())
        s["structuur"] = r["ONDERWIJSSTRUCTUUR"].strip()
        out.append(s)
    return out


def geo_key(s):
    if not s["pc6"] or s["hn"] is None:
        return None
    return "%s|%d|%s" % (s["pc6"], s["hn"], s["suf"])
