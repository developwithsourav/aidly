"""Measures how much of each page actually carries content.

Renders every page and finds the lowest non white pixel above the footer rule,
which is a truer measure of wasted space than a word count.
"""
import sys
import pypdfium2 as pdfium
from PIL import Image

PDF = sys.argv[1] if len(sys.argv) > 1 else \
    r"G:\Claude\Projects\aegis\docs\Aidly_SE_Report.pdf"

doc = pdfium.PdfDocument(PDF)
print("pages:", len(doc))
bad = []
for i in range(len(doc)):
    im = doc[i].render(scale=1.0).to_pil().convert("L")
    w, h = im.size
    # ignore the footer band, which always has the rule and page number
    body = im.crop((0, 0, w, int(h * 0.92)))
    px = body.load()
    bw, bh = body.size
    last = 0
    for y in range(bh - 1, -1, -1):
        row_has_ink = False
        for x in range(0, bw, 3):
            if px[x, y] < 235:
                row_has_ink = True
                break
        if row_has_ink:
            last = y
            break
    top_margin = int(bh * 0.055)
    usable = bh - top_margin
    fill = max(0.0, (last - top_margin) / usable)
    flag = ""
    if fill < 0.60:
        flag = "  <-- WASTED"
        bad.append((i + 1, round(fill * 100)))
    print(f"  p{i+1:>3}  fill {fill*100:5.1f}%{flag}")

print()
print("pages under 60% fill:", bad)
print("count:", len(bad))
