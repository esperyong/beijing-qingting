"""Make contact sheets of candidate photos so a person can pick the best ones.

One row per taxon: up to 5 male candidates, then up to 5 female candidates,
then up to 3 more (unknown sex, Beijing first). Each thumbnail is labelled with
its pick key (m0..m4, f0..f4, x0..x2), BJ/CN, and fave count.

Run from the repo root:
  python3 -P scripts/contact_sheets.py OUT_DIR TAXON_ID [TAXON_ID ...]
Writes OUT_DIR/sheet-<n>.jpg (6 rows each) and OUT_DIR/keys.json.
"""
import concurrent.futures as cf
import io, json, pathlib, sys, time, urllib.error, urllib.request
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAND = ROOT / "data" / "cache" / "cand"
THUMB = ROOT / "data" / "cache" / "thumb"
THUMB.mkdir(parents=True, exist_ok=True)
W, H = 200, 150
FONT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 16) \
    if pathlib.Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc").exists() else ImageFont.load_default()


def rank(c):
    return (-int(c["beijing"]), -int(c["china"]), -c["faves"], c["pos"])


def rank_quality(c):
    return (-c["faves"], -int(c["china"]), c["pos"])


def pick_lists(cands):
    adult = [c for c in cands if c.get("stage") in (None, "adult", "teneral")]
    males = sorted([c for c in adult if c["sex"] == "male" and c["pos"] == 0], key=rank_quality)
    fems = sorted([c for c in adult if c["sex"] == "female" and c["pos"] == 0], key=rank_quality)
    # Beijing photos first among the males/females if any, then the most-faved.
    bj_m = [c for c in males if c["beijing"]][:2]
    bj_f = [c for c in fems if c["beijing"]][:2]
    m = (bj_m + [c for c in males if c not in bj_m])[:5]
    f = (bj_f + [c for c in fems if c not in bj_f])[:5]
    used = {c["photo"] for c in m + f}
    rest = sorted([c for c in adult if c["photo"] not in used and c["sex"] is None and c["pos"] == 0], key=rank)[:3]
    return m, f, rest


def thumb(c):
    p = THUMB / f'{c["photo"]}.jpg'
    if not p.exists():
        url = c["small"] if "small" in c else c["url"].format(size="small")
        req = urllib.request.Request(url, headers={"User-Agent": "beijing-qingting/0.1 (https://github.com/esperyong/beijing-qingting)"})
        for i in range(6):
            try:
                if "small" in c:
                    time.sleep(0.6)
                data = urllib.request.urlopen(req, timeout=40).read()
                break
            except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
                if i == 5 or (isinstance(e, urllib.error.HTTPError) and e.code not in (429, 500, 502, 503, 504)):
                    raise
                time.sleep(5 * (i + 1))
        p.write_bytes(data)
    return p


def commons_lists(name):
    import hashlib, re
    p = ROOT / "data" / "cache" / "commons" / (name.replace(" ", "_") + ".json")
    if not p.exists():
        return [], [], []
    cs = json.loads(p.read_text())
    for c in cs:
        c["photo"] = "c" + hashlib.sha1(c["title"].encode()).hexdigest()[:10]
        c["small"] = re.sub(r"/\d+px-", "/330px-", c["thumb"]) if c.get("thumb") else c["url"]
        c["beijing"], c["china"], c["faves"] = False, False, 9 if c["why"] != "any" else 0
    q = lambda c: (c["why"] == "any",)
    m = sorted([c for c in cs if c["sex"] == "male"], key=q)[:5]
    f = sorted([c for c in cs if c["sex"] == "female"], key=q)[:5]
    x = sorted([c for c in cs if c["sex"] not in ("male", "female")], key=q)[:3]
    return m, f, x


def main():
    import yaml
    out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    want = {int(a) for a in sys.argv[2:] if not a.startswith("t")}
    raw = [int(a[1:]) for a in sys.argv[2:] if a.startswith("t")]
    species = yaml.safe_load(open(ROOT / "data" / "species.yaml"))
    taxa_json = json.loads((ROOT / "data" / "cache" / "taxa.json").read_text())
    rows, keys = [], {}
    names = {}
    for t in raw:
        m, f, x = pick_lists(json.loads((CAND / f"{t}.json").read_text()))
        row = [(f"m{i}", c) for i, c in enumerate(m)] + [(f"f{i}", c) for i, c in enumerate(f)] + [(f"x{i}", c) for i, c in enumerate(x)]
        keys[f"t{t}"] = {k: c["photo"] for k, c in row}
        names[f"t{t}"] = f"t{t}"
        rows.append((f"t{t}", row))
    for s in species if want else []:
        if want and s["id"] not in want:
            continue
        lc = s.get("list_cn", s.get("cn"))
        t = s.get("inat") or ((taxa_json.get(lc) or {}).get("inat") or {}).get("id")
        if t and (CAND / f"{t}.json").exists():
            m, f, x = pick_lists(json.loads((CAND / f"{t}.json").read_text()))
            row = [(f"m{i}", c) for i, c in enumerate(m)] + [(f"f{i}", c) for i, c in enumerate(f)] + [(f"x{i}", c) for i, c in enumerate(x)]
            keys[f'{s["id"]}'] = {k: c["photo"] for k, c in row}
            names[f'{s["id"]}'] = f'{s["id"]} {lc}'
            rows.append((f'{s["id"]}', row))
        sci = s.get("sci") or ""
        if sci and not sci.endswith("sp."):
            m, f, x = commons_lists(" ".join(sci.split()[:2]))
            if m or f or x:
                row = [(f"m{i}", c) for i, c in enumerate(m)] + [(f"f{i}", c) for i, c in enumerate(f)] + [(f"x{i}", c) for i, c in enumerate(x)]
                keys[f'{s["id"]}c'] = {k: c["title"] for k, c in row}
                names[f'{s["id"]}c'] = f'  ↳ Commons'
                rows.append((f'{s["id"]}c', row))
    allc = [c for _, r in rows for _, c in r]
    with cf.ThreadPoolExecutor(8) as ex:
        list(ex.map(thumb, [c for c in allc if "small" not in c]))
    for c in allc:
        if "small" in c:
            thumb(c)
    per = 6
    for s in range(0, len(rows), per):
        chunk = rows[s:s + per]
        sheet = Image.new("RGB", (160 + 13 * (W + 4), len(chunk) * (H + 26)), "white")
        d = ImageDraw.Draw(sheet)
        for r, (t, row) in enumerate(chunk):
            y = r * (H + 26)
            d.text((4, y + 4), names.get(t, str(t)), fill="black", font=FONT)
            for k, c in row:
                col = {"m": 0, "f": 5, "x": 10}[k[0]] + int(k[1:])
                x0 = 160 + col * (W + 4)
                im = Image.open(THUMB / f'{c["photo"]}.jpg').convert("RGB")
                im.thumbnail((W, H))
                sheet.paste(im, (x0 + (W - im.width) // 2, y + (H - im.height) // 2))
                tag = f'{k} {"BJ" if c["beijing"] else "CN" if c["china"] else ""} ♥{c["faves"]}'
                d.rectangle((x0, y + H, x0 + W, y + H + 24), fill="#222" if k[0] == "m" else "#8a2d4a" if k[0] == "f" else "#555")
                d.text((x0 + 4, y + H + 2), tag, fill="white", font=FONT)
        sheet.save(out / f"sheet-{s // per + 1}.jpg", quality=82)
    (out / "keys.json").write_text(json.dumps(keys, indent=1))
    print("sheets:", (len(rows) + per - 1) // per)


if __name__ == "__main__":
    main()
