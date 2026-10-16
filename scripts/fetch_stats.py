"""Fetch per-species iNaturalist statistics for the page.

For each taxon: verifiable observations by month in Beijing and in China, and
the open (not obscured) Beijing observation points. Caches to
data/cache/stats/<taxon>.json.

Run from the repo root: python3 scripts/fetch_stats.py [taxon_id ...]
"""
import json, pathlib, sys, time, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fetch_candidates import taxa_from_species  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "cache" / "stats"
OUT.mkdir(parents=True, exist_ok=True)
API = "https://api.inaturalist.org/v1"
BEIJING, CHINA = 6907, 6903


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "beijing-qingting/0.1 (species guide)"})
    for i in range(5):
        try:
            time.sleep(1.1)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            if i == 4:
                raise
            time.sleep(3 + 5 * i)


def months(taxon, place):
    d = get(f"{API}/observations/histogram?taxon_id={taxon}&place_id={place}&verifiable=true"
            "&date_field=observed&interval=month_of_year")
    m = d["results"]["month_of_year"]
    return [m.get(str(i), 0) for i in range(1, 13)]


def points(taxon):
    pts, page = [], 1
    while True:
        d = get(f"{API}/observations?taxon_id={taxon}&place_id={BEIJING}&verifiable=true&per_page=200&page={page}"
                "&order_by=observed_on&order=desc")
        for o in d["results"]:
            if o.get("obscured") or not o.get("location"):
                continue
            lat, lon = map(float, o["location"].split(","))
            pts.append({"lat": round(lat, 4), "lon": round(lon, 4), "date": o.get("observed_on"),
                        "obs": o["id"], "rg": o.get("quality_grade") == "research"})
        if page * 200 >= d["total_results"] or page >= 5:
            return pts, d["total_results"]
        page += 1


def fetch(taxon):
    path = OUT / f"{taxon}.json"
    if path.exists():
        return json.loads(path.read_text())
    pts, total = points(taxon)
    d = {"taxon": taxon, "months_bj": months(taxon, BEIJING), "months_cn": months(taxon, CHINA),
         "bj_total": total, "points": pts}
    path.write_text(json.dumps(d, ensure_ascii=False))
    return d


def main():
    todo = [(0, "", int(t)) for t in sys.argv[1:]] or taxa_from_species()
    for sid, cn, tid in todo:
        d = fetch(tid)
        print(f"{sid:>2} {cn:<14} {tid:<8} BJ {d['bj_total']:>4} open {len(d['points']):>4}  months {d['months_bj']}", flush=True)


if __name__ == "__main__":
    main()
