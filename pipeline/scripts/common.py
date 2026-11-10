"""Shared helpers. Scripts are run as `python -I script.py`; each script adds its own
directory to sys.path explicitly (scripts/ holds only our code, raw/ holds untrusted data)."""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.dirname(HERE)
RAW = os.path.join(DATA, "raw")
OUT = os.path.join(DATA, "out")
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

UA = "Schoollijn-open-data-build/1.0 (static site data pipeline; DUO/CBS/PDOK open data)"

# Data years (single source of truth, echoed in out/meta.json)
PO_PUPIL_FILE = "bo_leerlingen_2025-2026.csv"
PO_ADVICE_FILE = "bo_advies_2024-2025.csv"
VO_PUPIL_FILE = "vo_leerlingen_2025.csv"
VO_EXAM_FILE = "vo_examens_2024-2025.csv"
SO_PUPIL_FILE = "so_leerlingen_2025-2026.csv"


def read_jsonl(path):
    """Read a JSONL checkpoint. A torn last line (crash mid-write) is ignored."""
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


class JsonlAppender:
    """Append one JSON object per line; flush + fsync after every record."""

    def __init__(self, path):
        self.path = path
        # make sure the file ends with a newline (in case of a torn last line)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, "rb") as f:
                f.seek(-1, os.SEEK_END)
                last = f.read(1)
            if last != b"\n":
                with open(path, "ab") as f:
                    f.write(b"\n")
        self.f = open(path, "a", encoding="utf-8", newline="\n")

    def write(self, obj):
        self.f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.f.flush()
        os.fsync(self.f.fileno())

    def close(self):
        self.f.close()


class Throttle:
    def __init__(self, per_second):
        self.gap = 1.0 / per_second
        self.last = 0.0

    def wait(self):
        d = self.last + self.gap - time.monotonic()
        if d > 0:
            time.sleep(d)
        self.last = time.monotonic()


def http_get(url, timeout=60, tries=6):
    """GET with retry + exponential backoff on 429/5xx/network errors. Returns bytes."""
    delay = 2.0
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/csv, */*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                ra = e.headers.get("Retry-After")
                time.sleep(float(ra) if ra and ra.isdigit() else delay)
                delay = min(delay * 2, 60)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if attempt < tries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise


def http_get_json(url, **kw):
    return json.loads(http_get(url, **kw).decode("utf-8"))


def write_json_atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
