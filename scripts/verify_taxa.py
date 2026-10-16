"""Check every draft scientific name in data/species.yaml against iNaturalist and GBIF.

Writes data/cache/taxa.json (raw answers) and prints a review table.
Run from the repo root: python3 scripts/verify_taxa.py
"""
import json, pathlib, time, urllib.parse, urllib.request
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
BEIJING = 6907  # iNaturalist place id for Beijing, CN


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "beijing-qingting/0.1"})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if i == 3:
                raise
            time.sleep(2 + 3 * i)


def inat_taxon(name):
    q = urllib.parse.quote(name)
    d = get(f"https://api.inaturalist.org/v1/taxa?q={q}&taxon_id=47792&locale=zh-CN&per_page=5&all_names=true")
    res = d["results"]
    exact = [r for r in res if r["name"].lower() == name.lower()]
    return (exact or res or [None])[0]


def inat_count(taxon_id, place=None, extra=""):
    p = f"&place_id={place}" if place else ""
    d = get(f"https://api.inaturalist.org/v1/observations?taxon_id={taxon_id}{p}&per_page=0&verifiable=true{extra}")
    return d["total_results"]


def gbif(name):
    d = get("https://api.gbif.org/v1/species/match?verbose=true&class=Insecta&name=" + urllib.parse.quote(name))
    return {k: d.get(k) for k in ("usageKey", "scientificName", "status", "matchType", "rank", "acceptedUsageKey", "species", "family")}


def main():
    sp = yaml.safe_load(open(ROOT / "data" / "species.yaml"))
    out = {}
    for s in sp:
        name = s.get("sci")
        if not name or name.endswith(" sp."):
            continue
        t = inat_taxon(name)
        row = {"query": name}
        if t:
            row["inat"] = {
                "id": t["id"], "name": t["name"], "rank": t["rank"], "is_active": t.get("is_active"),
                "zh": t.get("preferred_common_name"), "matched_term": t.get("matched_term"),
                "global_obs": t.get("observations_count"),
                "photo": (t.get("default_photo") or {}).get("medium_url"),
                "ancestry_family": next((a for a in []), None),
            }
            row["inat"]["beijing_obs"] = inat_count(t["id"], BEIJING)
            row["inat"]["beijing_rg"] = inat_count(t["id"], BEIJING, "&quality_grade=research")
            row["inat"]["china_obs"] = inat_count(t["id"], 6903)
        row["gbif"] = gbif(name)
        out[s["cn"]] = row
        i = row.get("inat", {})
        g = row["gbif"]
        print(f'{s["id"]:>2} {s["cn"]:<14} {name:<34} | iNat: {i.get("name","-"):<32} {str(i.get("zh")):<10} BJ {i.get("beijing_obs","-"):>4}/{i.get("beijing_rg","-"):<4} CN {i.get("china_obs","-"):>5} | GBIF: {g.get("scientificName")} [{g.get("status")}/{g.get("matchType")}]', flush=True)
        time.sleep(1)
    (CACHE / "taxa.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
