"""Build docs/index.html, the Beijing dragonfly guide.

Inputs (all under data/):
  species.yaml   the 84 taxa: names, accepted scientific name, verdict, notes
  tiers.yaml     老姜's S/A/B/C rarity lists (species + sex + colour form)
  photos.yaml    the photos picked for each taxon (iNaturalist or Wikimedia Commons)
  text.yaml      page copy: lede, primer, family blurbs, notes, sources
  cache/         API answers from the fetch_*.py scripts
  geo/           Beijing boundary (DataV, GCJ-02; converted to WGS-84 here)
Outputs:
  docs/index.html and docs/photos/<key>-s.jpg (480 px) / <key>-l.jpg (1600 px)

Run from the repo root: python3 -P scripts/build.py   (add --no-download to skip new photos)
"""
import hashlib, html, io, json, math, pathlib, re, sys, time, urllib.request
import yaml
from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, CACHE, DOCS = ROOT / "data", ROOT / "data" / "cache", ROOT / "docs"
PHOTOS = DOCS / "photos"
PHOTOS.mkdir(parents=True, exist_ok=True)
ORIG = CACHE / "orig"
ORIG.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "beijing-qingting/0.1 (https://github.com/esperyong/beijing-qingting)"}
LIC_NAME = {"cc0": "CC0", "cc-by": "CC BY", "cc-by-sa": "CC BY-SA", "cc-by-nc": "CC BY-NC", "cc-by-nc-sa": "CC BY-NC-SA"}


def load(name):
    return yaml.safe_load(open(DATA / name, encoding="utf-8"))


def esc(s):
    return html.escape(str(s), quote=True)


# ------------------------------------------------------------------ photos

def inat_index():
    idx = {}
    for p in (CACHE / "cand").glob("*.json"):
        for c in json.loads(p.read_text()):
            idx.setdefault(c["photo"], c)
    return idx


def commons_index():
    idx = {}
    for p in (CACHE / "commons").glob("*.json"):
        for c in json.loads(p.read_text()):
            idx.setdefault(c["title"], c)
    return idx


def download(url, dest):
    if dest.exists():
        return dest
    req = urllib.request.Request(url, headers=UA)
    for i in range(6):
        try:
            if "wikimedia" in url:
                time.sleep(1.0)
            with urllib.request.urlopen(req, timeout=90) as r:
                dest.write_bytes(r.read())
            return dest
        except Exception as e:  # noqa: BLE001
            print(f"  retry {i + 1} {url[:80]}: {e}", file=sys.stderr)
            time.sleep(5 * (i + 1))
    return dest


def derive(src_path, key):
    s, l = PHOTOS / f"{key}-s.jpg", PHOTOS / f"{key}-l.jpg"
    if s.exists() and l.exists():
        with Image.open(l) as im:
            return im.size
    im = ImageOps.exif_transpose(Image.open(src_path)).convert("RGB")
    big = im.copy()
    big.thumbnail((1600, 1600), Image.LANCZOS)
    big.save(l, "JPEG", quality=80, optimize=True, progressive=True)
    small = im.copy()
    small.thumbnail((480, 480 * 2), Image.LANCZOS)
    if small.width > 480:
        small = small.resize((480, round(small.height * 480 / small.width)), Image.LANCZOS)
    small.save(s, "JPEG", quality=76, optimize=True, progressive=True)
    return big.size


def resolve_photo(pick, inat, commons, offline):
    if pick["src"] == "inat":
        c = inat[int(pick["id"])]
        key = f'i{c["photo"]}'
        orig = ORIG / f"{key}.jpg"
        if not offline:
            download(c["url"].format(size="original"), orig)
        place = pick.get("place") or c.get("place") or ""
        meta = {"by": c["user_name"], "lic": LIC_NAME.get(c["license"], c["license"]),
                "link": f'https://www.inaturalist.org/observations/{c["obs"]}', "srcName": "iNaturalist",
                "date": c.get("observed_on") or "", "place": place, "bj": bool(c.get("beijing"))}
    else:
        c = commons[pick["id"]]
        key = "c" + hashlib.sha1(c["title"].encode()).hexdigest()[:10]
        orig = ORIG / f"{key}.jpg"
        if not offline:
            download(c["thumb"] or c["url"], orig)
        by = re.sub(r"\s+", " ", c.get("artist") or "").strip() or "Wikimedia Commons"
        meta = {"by": by[:60], "lic": c["license"], "link": c["page"], "srcName": "Wikimedia Commons",
                "date": c.get("date") or "", "place": pick.get("place") or "", "bj": False}
    if not orig.exists():
        return None
    w, h = derive(orig, key)
    meta.update({"s": f"photos/{key}-s.jpg", "l": f"photos/{key}-l.jpg", "m": f"photos/{key}-l.jpg", "w": w, "h": h,
                 "sex": pick["sex"], "form": pick.get("form", ""), "pos": pick.get("pos", "50% 50%")})
    return meta


# ------------------------------------------------------------------ map

def gcj_to_wgs(lon, lat):
    a, ee = 6378245.0, 0.00669342162296594323

    def tlat(x, y):
        r = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        r += (20 * math.sin(6 * x * math.pi) + 20 * math.sin(2 * x * math.pi)) * 2 / 3
        r += (20 * math.sin(y * math.pi) + 40 * math.sin(y / 3 * math.pi)) * 2 / 3
        r += (160 * math.sin(y / 12 * math.pi) + 320 * math.sin(y * math.pi / 30)) * 2 / 3
        return r

    def tlon(x, y):
        r = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        r += (20 * math.sin(6 * x * math.pi) + 20 * math.sin(2 * x * math.pi)) * 2 / 3
        r += (20 * math.sin(x * math.pi) + 40 * math.sin(x / 3 * math.pi)) * 2 / 3
        r += (150 * math.sin(x / 12 * math.pi) + 300 * math.sin(x / 30 * math.pi)) * 2 / 3
        return r

    dlat, dlon = tlat(lon - 105, lat - 35), tlon(lon - 105, lat - 35)
    rad = lat / 180 * math.pi
    m = 1 - ee * math.sin(rad) ** 2
    sm = math.sqrt(m)
    dlat = (dlat * 180) / ((a * (1 - ee)) / (m * sm) * math.pi)
    dlon = (dlon * 180) / (a / sm * math.cos(rad) * math.pi)
    return lon - dlon, lat - dlat


class Proj:
    W = 300
    LON0, LON1, LAT0, LAT1 = 115.40, 117.53, 39.42, 41.08
    K = math.cos(math.radians(40.25))

    def __init__(self):
        self.s = self.W / ((self.LON1 - self.LON0) * self.K)
        self.H = round((self.LAT1 - self.LAT0) * self.s)

    def __call__(self, lon, lat):
        return round((lon - self.LON0) * self.K * self.s, 1), round((self.LAT1 - lat) * self.s, 1)


def rings(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [r for poly in geom["coordinates"] for r in poly]


def path(rs, proj, step=1):
    out = []
    for r in rs:
        pts = [proj(*gcj_to_wgs(*pt)) for pt in r[::step]]
        out.append("M" + "L".join(f"{x:g},{y:g}" for x, y in pts) + "Z")
    return "".join(out)


def districts_wgs():
    out = []
    for f in json.load(open(DATA / "geo" / "beijing_full.json"))["features"]:
        rs = [[gcj_to_wgs(*pt) for pt in r] for r in rings(f["geometry"])]
        out.append((f["properties"]["name"].replace("区", ""), rs))
    return out


def inside(lon, lat, ring):
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def district_of(lon, lat, dists):
    for name, rs in dists:
        if any(inside(lon, lat, r) for r in rs):
            return name
    return None


def bj_note(st, dists):
    pts = st.get("points", [])
    m = st.get("months_bj", [0] * 12)
    parts = []
    if len(pts) >= 3:
        cnt = {}
        for p in pts:
            d = district_of(p["lon"], p["lat"], dists)
            if d:
                cnt[d] = cnt.get(d, 0) + 1
        top = [d for d, _ in sorted(cnt.items(), key=lambda kv: -kv[1])[:3]]
        if top:
            parts.append("记录最多的区：" + "、".join(top))
    total = sum(m)
    if total >= 8:
        keep = [i for i, v in enumerate(m) if v >= max(m) * 0.15]
        peak = m.index(max(m)) + 1
        rng = f"{keep[0] + 1} 月" if keep[0] == keep[-1] else f"{keep[0] + 1}–{keep[-1] + 1} 月"
        parts.append(f"主要见于 {rng}，{peak} 月最多")
    return "；".join(parts) + ("。" if parts else "")


def build_map():
    proj = Proj()
    outline = path(rings(json.load(open(DATA / "geo" / "beijing.json"))["features"][0]["geometry"]), proj)
    full = json.load(open(DATA / "geo" / "beijing_full.json"))["features"]
    districts = path([r for f in full for r in rings(f["geometry"])], proj, step=2)
    labels = ""
    for name, lon, lat in (("延庆", 115.98, 40.47), ("怀柔", 116.63, 40.55), ("密云", 116.98, 40.48), ("昌平", 116.22, 40.22),
                           ("门头沟", 115.82, 39.97), ("房山", 115.86, 39.72), ("平谷", 117.12, 40.17), ("城区", 116.40, 39.91)):
        x, y = proj(lon, lat)
        labels += f'<text class="lb" x="{x}" y="{y}" text-anchor="middle">{name}</text>'
    return proj, {"w": proj.W, "h": proj.H, "outline": outline, "districts": districts, "labels": labels}


# ------------------------------------------------------------------ main

def main():
    offline = "--no-download" in sys.argv
    species, tiers, picks, text = load("species.yaml"), load("tiers.yaml"), load("photos.yaml") or {}, load("text.yaml")
    taxa = json.loads((CACHE / "taxa.json").read_text())
    inat, commons = inat_index(), commons_index()
    proj, bjmap = build_map()
    dists = districts_wgs()
    wol = json.loads((CACHE / "wol_index.json").read_text())
    by_cn = {s["list_cn"]: s for s in species}

    out, families = {}, {}
    for s in species:
        t = (taxa.get(s["list_cn"]) or {}).get("inat") or {}
        tid = s.get("inat", t.get("id"))
        stats_path = CACHE / "stats" / f"{tid}.json"
        st = json.loads(stats_path.read_text()) if tid and stats_path.exists() else {}
        photos = []
        for pk in picks.get(s["id"], []) or []:
            m = resolve_photo(pk, inat, commons, offline)
            if m:
                photos.append(m)
            else:
                print("  missing photo", s["id"], pk, file=sys.stderr)
        links = []
        if tid:
            links.append(["iNaturalist", f"https://www.inaturalist.org/taxa/{tid}"])
            links.append(["iNat 北京记录", f"https://www.inaturalist.org/observations?taxon_id={tid}&place_id=6907"])
        for l in s.get("links", []) or []:
            links.append(l)
        pts = [list(proj(p["lon"], p["lat"])) for p in st.get("points", [])]
        author = s.get("author", "")
        parts = s["sci"].split()
        w = wol.get(" ".join(parts[:2]))
        if w and (len(parts) == 2 or parts[2] == parts[1]):
            author = f'{w["author"]}, {w["year"]}'
            if w["original_genus"]:
                author = f"({author})"
        gbif = s.get("gbif") or ((taxa.get(s["list_cn"]) or {}).get("gbif") or {}).get("usageKey")
        if gbif and not s.get("sci", "").endswith("sp."):
            links.append(["GBIF", f"https://www.gbif.org/species/{gbif}"])
        if w:
            links.append(["世界蜻蜓名录", f'https://api.odonatacentral.org/wol/taxa/{w["id"]}/'])
        out[s["id"]] = {
            "id": s["id"], "list_cn": s["list_cn"], "cn": s["cn"], "sci": s["sci"], "author": author,
            "old": s.get("old", ""), "family": s["family"], "family_cn": text["families"][s["family"]]["cn"],
            "suborder": text["families"][s["family"]]["suborder"],
            "status": s["status"], "verdict": s["verdict"], "verdict_short": s.get("verdict_short", ""),
            "tips": s.get("tips", ""), "habitat": s.get("habitat", ""), "bj_note": bj_note(st, dists) if tid else "",
            "inat": tid, "bj": st.get("bj_total", 0), "cn_obs": sum(st.get("months_cn", [])) if st else 0,
            "months_bj": st.get("months_bj", [0] * 12), "months_cn": st.get("months_cn", [0] * 12),
            "pts": pts, "photos": photos, "links": links, "tiers": [],
        }
        families.setdefault(s["family"], []).append(s["id"])

    tier_out = []
    for key in ("S", "A", "B", "C"):
        t = tiers[key]
        items = []
        for it in t["items"]:
            sid = by_cn[it["cn"]]["id"]
            e = {"sp": sid, "sex": it["sex"], "form": it.get("form", "")}
            items.append(e)
            out[sid]["tiers"].append({"tier": key, "sex": it["sex"], "form": it.get("form", "")})
        tier_out.append({"key": key, "title": t["title"], "short": text["tiers"][key]["short"], "desc": text["tiers"][key]["desc"], "items": items})

    fam_out = []
    for key, f in text["families"].items():
        if key in families:
            fam_out.append({"key": key, "cn": f["cn"], "suborder": f["suborder"], "desc": f["desc"], "species": families[key]})

    shots = []
    for i, (fn, title, note) in enumerate(text["shots"]):
        src = DOCS / "images" / "beijing-qingting-classifications" / fn
        thumb = PHOTOS / f"shot-{i}.jpg"
        if not thumb.exists():
            im = Image.open(src).convert("RGB")
            im.thumbnail((720, 720))
            im.save(thumb, "JPEG", quality=80)
        shots.append({"s": f"photos/shot-{i}.jpg", "l": f"images/beijing-qingting-classifications/{fn}", "title": title, "note": note})

    # overview map: every open Beijing point, coloured by suborder
    dots = []
    for sp in out.values():
        cls = "pt" if sp["suborder"] == "Anisoptera" else "pt z"
        dots.extend(f'<circle class="{cls}" cx="{x}" cy="{y}" r="1.6"/>' for x, y in sp["pts"])
    big_map = (f'<svg class="bjmap" viewBox="0 0 {bjmap["w"]} {bjmap["h"]}" role="img" aria-label="北京蜻蜓公开记录点总览">'
               f'<path class="ol" d="{bjmap["outline"]}"/><path class="di" d="{bjmap["districts"]}"/>{bjmap["labels"]}{"".join(dots)}</svg>')
    n_pts = sum(len(sp["pts"]) for sp in out.values())
    n_obs = sum(sp["bj"] or 0 for sp in out.values())

    counts = {k: sum(1 for s in out.values() if s["status"] == k) for k in ("valid", "renamed", "undetermined", "doubtful")}
    fmt = {"n_pts": n_pts, "n_obs": n_obs, **{f"n_{k}": v for k, v in counts.items()},
           "n_with_photo": sum(1 for s in out.values() if s["photos"]), "n_photos": sum(len(s["photos"]) for s in out.values())}

    def fill(s):
        return s.format(**fmt) if isinstance(s, str) else s

    data = {
        "species": out, "order": [s["id"] for s in species], "tiers": tier_out, "families": fam_out,
        "tierTitle": {k: tiers[k]["title"] for k in tiers}, "suborders": text["suborders"],
        "verdictLabels": text["verdict_labels"], "missingText": text["missing"],
        "hero": text["hero"], "lede": fill(text["lede"]), "primer": fill(text["primer"]),
        "overview": fill(text["overview"].replace("{{MAP}}", "@@MAP@@")).replace("@@MAP@@", big_map), "notes": fill(text["notes"]), "footer": fill(text["footer"]),
        "shots": shots, "map": bjmap,
    }
    tpl = (ROOT / "scripts" / "template.html").read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    (DOCS / "index.html").write_text(tpl.replace("/*DATA*/", blob), encoding="utf-8")
    size = sum(p.stat().st_size for p in PHOTOS.glob("*.jpg"))
    print(f"docs/index.html written: {len(out)} taxa, {fmt['n_photos']} photos ({size/1e6:.1f} MB in docs/photos), "
          f"{n_pts} map points; verdicts {counts}")


if __name__ == "__main__":
    main()
