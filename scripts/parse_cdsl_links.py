from pathlib import Path
import re

p = Path(
    r"D:\TrendForge\data\raw_sources\institutional_endpoints\cdsl_fpi_fortnightly\2026-08-01\721020b94f01e54cbccd268f053d531b712870164078ffdc869491016dd3e63e.html"
)
t = p.read_text(encoding="utf-8", errors="replace")
print("len", len(t))
links = re.findall(r'href=["\']([^"\']+)["\']', t, re.I)
for link in links:
    low = link.lower()
    if any(x in low for x in ("xls", "xlsx", "csv", "pdf", "fpi", "fortnight", "download")):
        print(link)
print("total links", len(links))
print(links[:40])
