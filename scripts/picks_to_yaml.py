"""Turn a pick list (from reviewing contact sheets) into data/photos.yaml entries.

Pick line: `<species id>: <sheet> <key> <sex> [form] | ...` where sheet is a
label mapped to a keys.json on the command line, key is m0/f1/x2 (iNat) or
cm0/cf1/cx2 (Commons) or t<taxon>:m0, and sex is 雄/雌/- (unknown).
Usage: python3 scripts/picks_to_yaml.py PICKS.txt A=path/keys.json B=... > data/photos.yaml
"""
import json, sys

sheets = {a.split("=")[0]: json.load(open(a.split("=")[1])) for a in sys.argv[2:]}
print("# 每个物种选用的照片。src: inat 用 iNaturalist 照片 id；commons 用 Wikimedia Commons 文件名。")
print("# sex: 雄 / 雌 / 空（性别未标注）；form: 色型（同色系、黄色型……），和 tiers.yaml 对应。")
print("# 由 scripts/picks_to_yaml.py 从接触印样挑选结果生成，之后可以手改。")
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    sid, rest = line.split(":", 1)
    print(f"{sid.strip()}:")
    for part in rest.split("|"):
        bits = part.split()
        sheet, key, sex = bits[0], bits[1], bits[2]
        form = bits[3] if len(bits) > 3 else ""
        keys = sheets[sheet]
        if ":" in key:
            row, k = key.split(":")
        else:
            row, k = sid.strip(), key
        if k.startswith("c"):
            src, pid = "commons", keys[f"{row}c"][k[1:]]
            pid = json.dumps(pid, ensure_ascii=False)
        else:
            src, pid = "inat", keys[row][k]
        sx = "" if sex == "-" else sex
        extra = f", form: {form}" if form else ""
        print(f"  - {{src: {src}, id: {pid}, sex: \"{sx}\"{extra}}}")
