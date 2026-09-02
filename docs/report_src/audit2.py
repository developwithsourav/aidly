"""Second pass: what the rendered PDF actually contains, page by page."""
import re
from collections import defaultdict

from pypdf import PdfReader

PDF = r"G:\Claude\Projects\aegis\docs\Aidly_SE_Report.pdf"
r = PdfReader(PDF)
pages = [(p.extract_text() or "") for p in r.pages]
print("pages:", len(pages))

CAP = re.compile(r"(Figure|Table|Listing)\s+(\d+\.\d+)\s+([A-Z][^\n]{0,80})")

print("\n" + "=" * 72)
print("CAPTIONS AS THEY APPEAR IN THE PDF")
seen = defaultdict(list)
for i, t in enumerate(pages, 1):
    for m in CAP.finditer(t):
        key = f"{m.group(1)} {m.group(2)}"
        cap = m.group(3).strip()
        # a caption, not a mid sentence reference
        if len(cap.split()) >= 2 and not cap[0].islower():
            seen[key].append((i, cap[:70]))
for k in sorted(seen, key=lambda s: (s.split()[0], [int(x) for x in s.split()[1].split(".")])):
    occ = seen[k]
    flag = "   <== APPEARS %d TIMES" % len(occ) if len(occ) > 1 else ""
    print(f"  {k:<12}{flag}")
    for pg, cap in occ:
        print(f"      p{pg:<3} {cap}")

print("\n" + "=" * 72)
print("TOC PAGE NUMBERS vs WHERE HEADINGS ACTUALLY START")
toc_txt = pages[1] + pages[2] if len(pages) > 2 else pages[1]
toc = re.findall(r"(\d+(?:\.\d+)?)\s+([A-Z][A-Za-z ,:0-9]+?)\s+(\d{1,3})\b", toc_txt)
actual = {}
for i, t in enumerate(pages, 1):
    for m in re.finditer(r"^(\d+\.\d+)\s+([A-Z][^\n]{3,60})$", t, re.M):
        actual.setdefault(m.group(1), i)
    for m in re.finditer(r"\n(\d)\n([A-Z][A-Za-z ]{5,50})\n", t):
        actual.setdefault(m.group(1), i)
bad = 0
for num, title, pg in toc:
    a = actual.get(num)
    if a is None:
        continue
    if int(pg) != a:
        print(f"  {num:<6} {title[:34]:<36} TOC says {pg:<4} actually starts p{a}")
        bad += 1
print("  mismatches:", bad, "of", len(toc), "entries parsed")

print("\n" + "=" * 72)
print("SUSPECT STRINGS")
for i, t in enumerate(pages, 1):
    for pat, why in ((r"\b223\b", "possible 22 + '3 | Page' run together"),
                     (r"24/48\d{3}", "roll number"),
                     (r"Listing 7\.9", "listing 7.9 location"),
                     (r"Section 7\.11", "section 7.11 reference")):
        for m in re.finditer(pat, t):
            s = max(0, m.start() - 60)
            frag = t[s:m.end() + 60].replace("\n", " ")
            print(f"  p{i:<3} [{why}] ...{frag}...")
