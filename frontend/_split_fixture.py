"""Split TRENDFORGE_FINAL_PRODUCT.html into css + js for the live host."""
import re
from pathlib import Path

src = Path(r"D:\TrendForge\docs\TRENDFORGE_FINAL_PRODUCT.html").read_text(encoding="utf-8")
css = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
js = re.search(r"<script>(.*?)</script>", src, re.S).group(1)
body = re.search(r"<body>(.*?)<script>", src, re.S).group(1)
out = Path(r"D:\TrendForge\frontend")
(out / "theme-final.css").write_text(
    "/* Exact visual copy of docs/TRENDFORGE_FINAL_PRODUCT.html */\n" + css + "\n",
    encoding="utf-8",
)
(out / "product-fixture.js").write_text(
    "/* Visual product renderer copied from TRENDFORGE_FINAL_PRODUCT.html.\n"
    "   Values are FIXTURE. They are not live market evidence. */\n"
    "(function () {\n"
    + js
    + "\nwindow.TrendForgeProductFixture = { go: typeof go === 'function' ? go : null };\n"
    "})();\n",
    encoding="utf-8",
)
(out / "_fixture_body.html").write_text(body, encoding="utf-8")
print("css", len(css), "js", len(js), "body", len(body))
