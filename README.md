# beijing-qingting

北京蜻蜓社的物种名录页：老姜（社长）统计的 84 条北京蜻蜓，按 S 传说、A 罕见、B 少见、C 常见四级分级，逐条核对了学名和分类现状，配上可公开使用的照片和 iNaturalist 上的北京记录。

打开 `docs/index.html` 就能看（照片在 `docs/photos/`，要和页面放在一起）。

## 文件

| 路径 | 内容 |
|---|---|
| `data/species.yaml` | 84 条名单：名单原文、核查后的学名、核查结论、识别要点、生境 |
| `data/tiers.yaml` | 老姜的 S/A/B/C 分级，单位是“种 + 性别 + 色型”，共 116 条 |
| `data/photos.yaml` | 每个物种选用的照片（iNaturalist 照片 id 或 Wikimedia Commons 文件名）和性别、色型 |
| `data/text.yaml` | 页面文案、各科简介、来源列表 |
| `data/cache/` | iNaturalist、Commons、世界蜻蜓名录的接口返回，重建页面时用 |
| `scripts/template.html` | 页面的样式和交互（稀有度 / 科属 / 名录核查表三种视图、物种详情、看大图） |
| `scripts/build.py` | 生成 `docs/index.html` 和 `docs/photos/` |
| `docs/images/beijing-qingting-classifications/` | 老姜的名单原图 |

## 重建

```sh
python3 -P scripts/build.py              # 下载新增照片并生成页面
python3 -P scripts/build.py --no-download  # 只用已有照片
```

需要 Python 3、PyYAML 和 Pillow。改了名单或结论，就改 `data/*.yaml` 再重建，不要手改 `docs/index.html`。

换照片：先跑 `scripts/fetch_candidates.py`（iNaturalist）和 `scripts/fetch_commons.py`（Commons）拿候选，用 `scripts/contact_sheets.py` 和 `scripts/zoom_sheet.py` 出接触印样挑图，再把选择写进 `data/photos.yaml`。北京的月份分布和记录点来自 `scripts/fetch_stats.py`，学名的命名人来自 `scripts/fetch_wol.py`。

## 照片许可

照片来自 iNaturalist 研究级观察和 Wikimedia Commons，许可为 CC0、CC BY、CC BY-SA、CC BY-NC 或 CC BY-NC-SA，页面上逐张标注了作者、许可和原图链接。带 NC 的照片只能用于非商业用途。
