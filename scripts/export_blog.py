"""Copy the built guide into leonblog as a static page under public/beijing-qingting/.

The blog serves it at https://blog.leonliu.cn/beijing-qingting/. The page links its
photos with relative paths, so the copy gets <base href="/beijing-qingting/"> to keep
them working when the URL is opened without the trailing slash.

Run from the repo root after build.py:
  python3 scripts/export_blog.py ../leonblog
Then in leonblog: pnpm run deploy (see its skills/blog-publish/SKILL.md, mode 4).
"""
import pathlib, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
NAME = "beijing-qingting"


def sync(src, dst):
    """Mirror src into dst: copy new or changed files, delete files src no longer has."""
    dst.mkdir(parents=True, exist_ok=True)
    keep = set()
    for f in src.iterdir():
        if f.is_file():
            keep.add(f.name)
            t = dst / f.name
            if not t.exists() or t.stat().st_size != f.stat().st_size:
                shutil.copy2(f, t)
    for t in dst.iterdir():
        if t.is_file() and t.name not in keep:
            t.unlink()


def main():
    blog = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / "leonblog").resolve()
    out = blog / "public" / NAME
    if not (blog / "astro.config.mjs").exists():
        sys.exit(f"{blog} doesn't look like the leonblog repo")
    page = (DOCS / "index.html").read_text(encoding="utf-8")
    page = page.replace("<head>\n", f'<head>\n<base href="/{NAME}/">\n', 1)
    assert f'<base href="/{NAME}/">' in page
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    sync(DOCS / "photos", out / "photos")
    sync(DOCS / "images" / "beijing-qingting-classifications", out / "images" / "beijing-qingting-classifications")
    n = sum(1 for _ in out.rglob("*") if _.is_file())
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"{out}: {n} files, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
