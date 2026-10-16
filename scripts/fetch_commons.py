"""Collect candidate photos for every species from Wikimedia Commons.

Searches files mentioning the scientific name, Quality/Featured images first,
keeps licences that allow reuse with credit, and guesses sex from the title and
description. Caches to data/cache/commons/<slug>.json.

Run from the repo root: python3 scripts/fetch_commons.py ["Genus species" ...]
"""
import html, json, pathlib, re, sys, time, urllib.parse, urllib.request
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "cache" / "commons"
OUT.mkdir(parents=True, exist_ok=True)
API = "https://commons.wikimedia.org/w/api.php"
OK_LIC = re.compile(r"^(CC0|Public domain|PD|CC BY(-SA)? [0-9.]+|CC BY(-SA)?|Attribution|GFDL)", re.I)
MALE = re.compile(r"\b(male|males|m[aâ]le|m[äa]nnchen|maennchen|männlich)\b|♂|オス|雄|수컷", re.I)
FEMALE = re.compile(r"\b(female|females|femelle|weibchen|weiblich)\b|♀|メス|雌|암컷", re.I)
SKIP = re.compile(r"exuvi|larva|larve|nymph|emergence|schlupf|museum|specimen|collection|drawing|illustration|plate|map|wing venation", re.I)
PAIR = re.compile(r"tandem|mating|copula|paarung|wheel|accouplement|couple", re.I)


def get(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": 2})
    req = urllib.request.Request(url, headers={"User-Agent": "beijing-qingting/0.1 (https://github.com/esperyong/beijing-qingting)"})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            if i == 3:
                raise
            time.sleep(3 + 4 * i)


def strip(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def search(q, n):
    d = get({"action": "query", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": n,
             "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1600})
    pages = (d.get("query") or {}).get("pages", [])
    return sorted(pages, key=lambda p: p.get("index", 0))


def fetch(name):
    path = OUT / (name.replace(" ", "_") + ".json")
    if path.exists():
        return json.loads(path.read_text())
    seen, out = set(), []
    for why, q, n in (("quality", f'"{name}" incategory:Quality_images', 20),
                      ("featured", f'"{name}" incategory:Featured_pictures_on_Wikimedia_Commons', 10),
                      ("any", f'"{name}" filetype:bitmap', 40)):
        for p in search(q, n):
            if p["title"] in seen or not p.get("imageinfo"):
                continue
            seen.add(p["title"])
            ii = p["imageinfo"][0]
            if ii.get("mime") not in ("image/jpeg", "image/png"):
                continue
            em = ii.get("extmetadata", {})
            lic = strip(em.get("LicenseShortName", {}).get("value"))
            desc = strip(em.get("ImageDescription", {}).get("value"))
            text = p["title"] + " " + desc
            if not OK_LIC.match(lic) or SKIP.search(text) or name.lower() not in text.lower().replace("_", " "):
                continue
            sex = None
            if PAIR.search(text):
                sex = "pair"
            elif MALE.search(text) and not FEMALE.search(text):
                sex = "male"
            elif FEMALE.search(text) and not MALE.search(text):
                sex = "female"
            out.append({
                "why": why, "title": p["title"], "page": ii.get("descriptionurl"),
                "url": ii["url"], "thumb": ii.get("thumburl"), "w": ii.get("width"), "h": ii.get("height"),
                "license": lic, "license_url": em.get("LicenseUrl", {}).get("value"),
                "artist": strip(em.get("Artist", {}).get("value")), "credit": strip(em.get("Credit", {}).get("value")),
                "date": strip(em.get("DateTimeOriginal", {}).get("value"))[:10],
                "desc": desc[:300], "sex": sex,
            })
        time.sleep(1)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    return out


def main():
    names = sys.argv[1:]
    if not names:
        sp = yaml.safe_load(open(ROOT / "data" / "species.yaml"))
        names = [s["sci"] for s in sp if s.get("sci") and not s["sci"].endswith(" sp.")]
        names = [" ".join(n.split()[:2]) for n in names]
    for n in dict.fromkeys(names):
        c = fetch(n)
        q = sum(1 for x in c if x["why"] != "any")
        print(f"{n:<30} {len(c):>3} files, {q} quality/featured, m{sum(x['sex']=='male' for x in c)} f{sum(x['sex']=='female' for x in c)}", flush=True)


if __name__ == "__main__":
    main()
