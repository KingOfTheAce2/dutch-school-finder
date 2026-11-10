"""Minimal stdlib .xlsx reader (first worksheet, values as strings). Input is untrusted: zipfile + ElementTree only,
no formulas evaluated, size limits enforced."""
import re, zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MAX_PART = 200_000_000


def _read(z, name):
    info = z.getinfo(name)
    if info.file_size > MAX_PART:
        raise ValueError("xlsx part too large: " + name)
    return z.read(name)


def _col(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_xlsx(path, sheet=0):
    """Return a list of rows (lists of str, '' for empty)."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(_read(z, "xl/sharedStrings.xml"))
            for si in root.findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
        sheets = sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
        sheets.sort(key=lambda n: int(re.search(r"(\d+)\.xml", n).group(1)))
        rows = []
        for _, el in ET.iterparse(__import__("io").BytesIO(_read(z, sheets[sheet])), events=("end",)):
            if el.tag != "{%s}row" % NS["m"]:
                continue
            row = []
            for c in el.findall("m:c", NS):
                idx = _col(c.get("r"))
                while len(row) < idx:
                    row.append("")
                t = c.get("t")
                v = c.find("m:v", NS)
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
                else:
                    val = v.text if v is not None and v.text is not None else ""
                row.append(val)
            rows.append(row)
            el.clear()
    return rows


def read_xlsx_dicts(path, sheet=0):
    rows = read_xlsx(path, sheet)
    hdr = [h.strip() for h in rows[0]]
    out = []
    for r in rows[1:]:
        r = r + [""] * (len(hdr) - len(r))
        out.append(dict(zip(hdr, r)))
    return out


def read_ods(path, sheet=None):
    """Return {sheet_name: rows} for an .ods file (rows are lists of str). Repeated cells/rows expanded (capped)."""
    ns = {"t": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
          "x": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
          "o": "urn:oasis:names:tc:opendocument:xmlns:office:1.0"}
    T = "{%s}" % ns["t"]
    out = {}
    with zipfile.ZipFile(path) as z:
        info = z.getinfo("content.xml")
        if info.file_size > 1_000_000_000:
            raise ValueError("content.xml too large")
        root = ET.fromstring(z.read("content.xml"))
    for tb in root.iter(T + "table"):
        name = tb.get(T + "name")
        rows = []
        for tr in tb.iter(T + "table-row"):
            rep = min(int(tr.get(T + "number-rows-repeated", "1")), 3)
            cells = []
            for tc in tr:
                if tc.tag not in (T + "table-cell", T + "covered-table-cell"):
                    continue
                n = min(int(tc.get(T + "number-columns-repeated", "1")), 200)
                txt = "".join("".join(p.itertext()) for p in tc.findall("x:p", ns))
                cells.extend([txt] * n)
            while cells and cells[-1] == "":
                cells.pop()
            if cells:
                rows.extend([cells] * rep)
        out[name] = rows
    return out
