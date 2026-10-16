"""Show chosen candidates large, to check sex, colour form and sharpness.

Usage: python3 -P scripts/zoom_sheet.py KEYS_JSON OUT.jpg 5:f0 5:cf0 7:m2 ...
KEYS_JSON is the keys.json written by contact_sheets.py. A key with a leading
"c" (cf0, cm1, cx2) refers to the Wikimedia Commons row of that species.
"""
import hashlib, json, pathlib, re, sys, time, urllib.request
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
Z = ROOT / "data" / "cache" / "zoom"
Z.mkdir(parents=True, exist_ok=True)
FONT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 20)
UA = {"User-Agent": "beijing-qingting/0.1 (https://github.com/esperyong/beijing-qingting)"}


def commons_by_title():
    idx = {}
    for p in (ROOT / "data" / "cache" / "commons").glob("*.json"):
        for c in json.loads(p.read_text()):
            idx[c["title"]] = c
    return idx


def inat_by_photo():
    idx = {}
    for p in (ROOT / "data" / "cache" / "cand").glob("*.json"):
        for c in json.loads(p.read_text()):
            idx[c["photo"]] = c
    return idx


def fetch(url, dest):
    if not dest.exists():
        for i in range(5):
            try:
                time.sleep(0.5)
                dest.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
                break
            except Exception:  # noqa: BLE001
                time.sleep(4 * (i + 1))
    return dest


def main():
    keys = json.loads(pathlib.Path(sys.argv[1]).read_text())
    out = sys.argv[2]
    cm, inat = commons_by_title(), inat_by_photo()
    tiles = []
    for arg in sys.argv[3:]:
        sid, k = arg.split(":")
        if k.startswith("c"):
            title = keys[f"{sid}c"][k[1:]]
            c = cm[title]
            url = re.sub(r"/\d+px-", "/960px-", c["thumb"]) if c.get("thumb") else c["url"]
            dest = Z / ("c" + hashlib.sha1(title.encode()).hexdigest()[:10] + ".jpg")
            label = f"{arg} {c.get('sex') or ''} {c['license']}"
        else:
            pid = keys[sid][k]
            c = inat[pid]
            url = c["url"].format(size="medium")
            dest = Z / f"{pid}.jpg"
            label = f"{arg} {c.get('sex') or ''} {'BJ' if c['beijing'] else ''} {c.get('place') or ''}"[:48]
        tiles.append((fetch(url, dest), label))
    W, H, cols = 560, 420, 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (W + 6), rows * (H + 30)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (p, label) in enumerate(tiles):
        x, y = (i % cols) * (W + 6), (i // cols) * (H + 30)
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail((W, H))
            sheet.paste(im, (x + (W - im.width) // 2, y + (H - im.height) // 2))
        except Exception:  # noqa: BLE001
            d.text((x + 10, y + 10), "load failed", fill="red", font=FONT)
        d.rectangle((x, y + H, x + W, y + H + 28), fill="#222")
        d.text((x + 6, y + H + 3), label, fill="white", font=FONT)
    sheet.save(out, quality=85)


if __name__ == "__main__":
    main()
