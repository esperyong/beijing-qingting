"""Download the World Odonata List tree and index every species by name.

Writes data/cache/wol_index.json: {"Genus species": {id, author, year, original_genus, qualifier, family}}.
build.py takes authors from it (parentheses when original_genus is set).
Run from the repo root: python3 scripts/fetch_wol.py
"""
import json, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
URL = "https://api.odonatacentral.org/wol/taxa/tree/"


def main():
    tree_path = CACHE / "wol_tree.json"
    if not tree_path.exists():
        req = urllib.request.Request(URL, headers={"User-Agent": "beijing-qingting/0.1"})
        tree_path.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    idx = {}

    def walk(node, fam=None):
        if isinstance(node, dict):
            name = node.get("scientific_name", "")
            if name.endswith("idae"):
                fam = name
            if " " in name:
                idx[name] = {**{k: node.get(k) for k in ("id", "author", "year", "original_genus", "qualifier")}, "family": fam}
            for v in node.values():
                if isinstance(v, (list, dict)):
                    walk(v, fam)
        elif isinstance(node, list):
            for v in node:
                walk(v, fam)

    walk(json.loads(tree_path.read_text()))
    (CACHE / "wol_index.json").write_text(json.dumps(idx, ensure_ascii=False))
    print(len(idx), "species indexed")


if __name__ == "__main__":
    main()
