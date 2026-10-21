#!/usr/bin/env python3
"""構成図の本体 JS を HTML に組み立て、Chrome ヘッドレスで PNG にする。

使い方: render.py <本体.js> <出力.png> [--width 1400] [--height 970] [--scale 2]
同じ場所に <出力>.html も書き出す（座標の微調整時にブラウザで開いて確認できる）。
"""
import argparse, pathlib, subprocess, sys

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "assets"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

p = argparse.ArgumentParser()
p.add_argument("body"); p.add_argument("out")
p.add_argument("--width", type=int, default=1400)
p.add_argument("--height", type=int, default=970)
p.add_argument("--scale", type=int, default=2)
a = p.parse_args()

css = (ASSETS / "theme.css").read_text()
defs = (ASSETS / "defs.svg").read_text()
lib = (ASSETS / "lib.js").read_text()
body = pathlib.Path(a.body).read_text()
out = pathlib.Path(a.out).resolve()
html = out.with_suffix(".html")
html.write_text(
    f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>'
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{a.width}" height="{a.height}" viewBox="0 0 {a.width} {a.height}">{defs}</svg>'
    f'<script>{lib}\n{body}</script></body></html>'
)
r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--force-device-scale-factor={a.scale}", f"--window-size={a.width},{a.height}",
                    f"--screenshot={out}", html.as_uri()], capture_output=True, text=True)
if not out.exists():
    sys.exit(f"render failed: {r.stderr[-500:]}")
print(out)
