"""Collect candidate photos for every species from iNaturalist.

Only research-grade observations whose photo licence allows reuse with credit
(CC0, CC BY, CC BY-SA, CC BY-NC, CC BY-NC-SA; no ND, no all-rights-reserved).
For each taxon it asks for the most-faved males, females, Chinese and Beijing
observations, and caches the answers in data/cache/cand/<taxon>.json so reruns
only fetch new taxa.

Run from the repo root: python3 scripts/fetch_candidates.py [taxon_id ...]
"""
import json, pathlib, sys, time, urllib.request
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAND = ROOT / "data" / "cache" / "cand"
CAND.mkdir(parents=True, exist_ok=True)
API = "https://api.inaturalist.org/v1/observations"
LIC = "cc0,cc-by,cc-by-sa,cc-by-nc,cc-by-nc-sa"
BEIJING, CHINA = 6907, 6903
SEX = {10: "female", 11: "male", 20: None}
STAGE = {2: "adult", 3: "teneral", 5: "nymph", 6: "larva", 8: "juvenile"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "beijing-qingting/0.1 (species guide)"})
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            if i == 4:
                raise
            time.sleep(3 + 5 * i)


def query(taxon, extra, n=15):
    url = (f"{API}?taxon_id={taxon}&quality_grade=research&photos=true&photo_license={LIC}"
           f"&order_by=votes&order=desc&per_page={n}{extra}")
    time.sleep(1.1)
    return get(url)["results"]


def flatten(o, why):
    ann = {a["controlled_attribute_id"]: a["controlled_value_id"] for a in o.get("annotations", [])
           if (a.get("vote_score") or 0) >= 0}
    place_ids = set(o.get("place_ids") or [])
    out = []
    for i, p in enumerate(o["photos"][:3]):
        if p.get("license_code") not in LIC.split(","):
            continue
        out.append({
            "why": why,
            "obs": o["id"],
            "photo": p["id"],
            "pos": i,
            "url": p["url"].replace("/square.", "/{size}."),
            "license": p["license_code"],
            "attribution": p.get("attribution"),
            "dims": p.get("original_dimensions"),
            "user": o["user"]["login"],
            "user_name": o["user"].get("name") or o["user"]["login"],
            "observed_on": o.get("observed_on"),
            "place": o.get("place_guess"),
            "location": None if o.get("obscured") else o.get("location"),
            "beijing": BEIJING in place_ids,
            "china": CHINA in place_ids,
            "sex": SEX.get(ann.get(9)),
            "stage": STAGE.get(ann.get(1)),
            "faves": o.get("faves_count", 0),
            "taxon": o["taxon"]["name"],
        })
    return out


def fetch(taxon):
    path = CAND / f"{taxon}.json"
    if path.exists():
        return json.loads(path.read_text())
    plan = [
        ("beijing", f"&place_id={BEIJING}"),
        ("china_male", f"&place_id={CHINA}&term_id=9&term_value_id=11"),
        ("china_female", f"&place_id={CHINA}&term_id=9&term_value_id=10"),
        ("male", "&term_id=9&term_value_id=11"),
        ("female", "&term_id=9&term_value_id=10"),
        ("china", f"&place_id={CHINA}"),
        ("any", ""),
    ]
    seen, cands = set(), []
    for why, extra in plan:
        for o in query(taxon, extra):
            for c in flatten(o, why):
                if c["photo"] not in seen:
                    seen.add(c["photo"])
                    cands.append(c)
    path.write_text(json.dumps(cands, ensure_ascii=False, indent=0))
    return cands


def taxa_from_species():
    sp = yaml.safe_load(open(ROOT / "data" / "species.yaml"))
    taxa = json.loads((ROOT / "data" / "cache" / "taxa.json").read_text())
    out = []
    for s in sp:
        tid = s.get("inat") or (taxa.get(s["cn"], {}).get("inat") or {}).get("id")
        for extra in s.get("photo_taxa", []):
            out.append((s["id"], s["cn"], extra))
        if tid:
            out.append((s["id"], s["cn"], tid))
    return out


def main():
    todo = [(0, "", int(t)) for t in sys.argv[1:]] or taxa_from_species()
    for sid, cn, tid in todo:
        c = fetch(tid)
        by = {}
        for x in c:
            by[x["why"]] = by.get(x["why"], 0) + 1
        print(f"{sid:>2} {cn:<14} {tid:<8} {len(c):>3} photos  {by}", flush=True)


if __name__ == "__main__":
    main()
