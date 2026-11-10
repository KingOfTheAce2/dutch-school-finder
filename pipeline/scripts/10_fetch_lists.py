"""Step 1 of the feature enrichment: download snapshots of the association school lists
into raw/lists/ (git-ignored) and write raw/lists/MANIFEST.json (URL, date, size, sha256).
Polite: identified User-Agent, 1 request/second, robots.txt of each host allows these paths
(checked 2026-10-16). Skips files already present. Run with `python -I`.
LOWAN is deliberately NOT fetched (its disclaimer forbids copying), ibo.org answers 403 to
non-browser clients and its terms forbid scraping, tto.nl answers 403."""
import os, sys, json, time, hashlib, datetime, urllib.request, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW

UA = "SchoollijnBot/0.1 (research; contact via site)"
L = os.path.join(RAW, "lists")
os.makedirs(os.path.join(L, "technasium_net"), exist_ok=True)

A = "https://montessori.nl/professionals/wp-admin/admin-ajax.php?action=store_search&lat=52.1&lng=5.3&max_results=1000&search_radius=500&autoload=1"
B = "https://dalton.nl/wpd/wp-admin/admin-ajax.php?action=store_search&lat=52.1&lng=5.3&max_results=500&search_radius=500&autoload=1"
FILES = {
    "nuffic_tto_all.html": "https://www.nuffic.nl/onderwijssectoren/voortgezet-onderwijs/tweetalig-onderwijs/alle-tto-scholen-in-nederland",
    "montessori_ss.json": A,
    "dalton_ss.json": B,
    "vrije_onze.html": "https://www.vrijescholen.nl/onze-scholen",
    "jenaplan_vereniging.html": "https://jenaplan.nl/vereniging",
    "dis_schools.html": "https://www.dutchinternationalschools.nl/schools/",
    "sio_city.html": "https://sio.nl/information-for-families/find-a-school-by-city/",
    "technasium_netwerk.xml": "https://www.technasium.nl/netwerk-sitemap.xml",
}


def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    man_path = os.path.join(L, "MANIFEST.json")
    man = json.load(open(man_path, encoding="utf-8")) if os.path.exists(man_path) else {}
    today = datetime.date.today().isoformat()
    todo = dict(FILES)
    for name, url in list(todo.items()):
        pass
    for name, url in todo.items():
        path = os.path.join(L, name)
        if not os.path.exists(path):
            b = get(url)
            open(path, "wb").write(b)
            time.sleep(1.0)
        b = open(path, "rb").read()
        man.setdefault(name, {"url": url, "retrieved": today})
        man[name].update(size=len(b), sha256=hashlib.sha256(b).hexdigest())
    # technasium regional network pages (listed in the network sitemap)
    sm = open(os.path.join(L, "technasium_netwerk.xml"), encoding="utf-8").read()
    for u in re.findall(r"<loc>([^<]+)</loc>", sm):
        slug = u.rstrip("/").rsplit("/", 1)[-1]
        name = "technasium_net/%s.html" % slug
        path = os.path.join(L, name)
        if not os.path.exists(path):
            open(path, "wb").write(get(u))
            time.sleep(1.0)
        b = open(path, "rb").read()
        man.setdefault(name, {"url": u, "retrieved": today})
        man[name].update(size=len(b), sha256=hashlib.sha256(b).hexdigest())
    json.dump(man, open(man_path, "w", encoding="utf-8"), indent=1)
    print("manifest entries:", len(man))


if __name__ == "__main__":
    main()
