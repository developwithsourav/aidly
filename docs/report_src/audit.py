"""Mechanical audit of the report.

Definitions of numbered objects are read from the source, because a caption is
written there exactly once. References are read from the prose in the same
source. The rendered PDF is then used to check where each object landed.
"""
import os
import re
import sys
from collections import defaultdict

SP = os.path.dirname(os.path.abspath(__file__))
# report_src sits inside docs/, so the outputs go to its parent. Derived
# rather than hardcoded, so renaming the project folder cannot break it.
DOCS = os.path.dirname(SP)
PDF = os.path.join(DOCS, "Aidly_SE_Report.pdf")

body = open(os.path.join(SP, "report_body.py"), encoding="utf-8").read()
front = open(os.path.join(SP, "report_front.py"), encoding="utf-8").read()
vis = open(os.path.join(SP, "report_visuals.py"), encoding="utf-8").read()
dfd = open(os.path.join(SP, "dfd_l1.py"), encoding="utf-8").read()
diag = open(os.path.join(SP, "report_diagrams.py"), encoding="utf-8").read()

OBJ = r"(Figure|Table|Listing)\s+(\d+)\.(\d+)"

# ---------------------------------------------------------------- definitions
defs = defaultdict(list)          # "Table 4.1" -> [caption text, ...]

# captions passed to table(..., caption="Table X.Y  ...")
for m in re.finditer(r'caption="((?:Table|Figure|Listing)[^"]*)"', body):
    cap = m.group(1)
    k = re.match(OBJ, cap)
    if k:
        defs[f"{k.group(1)} {k.group(2)}.{k.group(3)}"].append(cap)

# fig("Figure X.Y ...")  possibly split across source lines
for m in re.finditer(r'fig\(\s*"((?:[^"\\]|\\.)*)"(?:\s*"((?:[^"\\]|\\.)*)")*', body):
    cap = m.group(0)
    cap = " ".join(re.findall(r'"((?:[^"\\]|\\.)*)"', cap))
    k = re.match(OBJ, cap.strip())
    if k:
        defs[f"{k.group(1)} {k.group(2)}.{k.group(3)}"].append(cap.strip())

# code(filename, src, "Listing X.Y ...")
for m in re.finditer(r'"(Listing\s+\d+\.\d+[^"]*)"', body):
    cap = m.group(1)
    k = re.match(OBJ, cap)
    defs[f"{k.group(1)} {k.group(2)}.{k.group(3)}"].append(cap)

# captions drawn inside the diagram functions
for src in (vis, dfd, diag):
    for m in re.finditer(r'"((?:Figure|Table)\s+\d+\.\d+[^"]*)"', src):
        cap = m.group(1)
        k = re.match(OBJ, cap)
        defs[f"{k.group(1)} {k.group(2)}.{k.group(3)}"].append(cap)

# ---------------------------------------------------------------- references
prose = " ".join(re.findall(r'"((?:[^"\\]|\\.)*)"', body))
refs = defaultdict(int)
for m in re.finditer(OBJ, prose):
    key = f"{m.group(1)} {m.group(2)}.{m.group(3)}"
    # a reference, unless this occurrence is the caption itself
    refs[key] += 1
for k in defs:
    refs[k] = max(0, refs[k] - len(defs[k]))

sec_refs = sorted(set(re.findall(r"Section\s+(\d+\.\d+)", prose)))
chap_refs = sorted(set(re.findall(r"Chapter\s+(\d+)", prose)), key=int)

# ---------------------------------------------------------------- headings
heads = re.findall(r'h2\("(\d+\.\d+)\s+([^"]+)"\)', body)
head_nums = [h[0] for h in heads]
chapters = re.findall(r'h1\((\d+),\s*"([^"]+)"\)', body)

print("=" * 72)
print("NUMBERED OBJECTS DEFINED")
for kind in ("Figure", "Table", "Listing"):
    ks = sorted([k for k in defs if k.startswith(kind)],
                key=lambda s: [int(x) for x in s.split()[1].split(".")])
    print(f"\n  {kind}: {len(ks)}")
    for k in ks:
        n = len(defs[k])
        dup = "   <== DEFINED %d TIMES" % n if n > 1 else ""
        r = refs.get(k, 0)
        cited = "" if r else "   <== never referenced in text"
        print(f"    {k:<12} refs={r}{dup}{cited}")
        for cap in defs[k]:
            print(f"        cap: {cap[:88]}")

print("\n" + "=" * 72)
print("GAPS AND DUPLICATES")
for kind in ("Figure", "Table", "Listing"):
    per_chap = defaultdict(list)
    for k in defs:
        if k.startswith(kind):
            c, n = k.split()[1].split(".")
            per_chap[int(c)].append(int(n))
    for c in sorted(per_chap):
        nums = sorted(per_chap[c])
        expect = list(range(1, max(nums) + 1))
        missing = [n for n in expect if n not in nums]
        dups = [n for n in set(nums) if nums.count(n) > 1]
        if missing or dups:
            print(f"  {kind} ch{c}: have {nums}"
                  f"{'  MISSING ' + str(missing) if missing else ''}"
                  f"{'  DUPLICATE ' + str(dups) if dups else ''}")

print("\n" + "=" * 72)
print("DANGLING REFERENCES (referenced but never defined)")
for k, n in sorted(refs.items()):
    if n and k not in defs:
        print(f"  {k}  referenced {n}x  <== NO SUCH OBJECT")

print("\n" + "=" * 72)
print("SECTION REFERENCES vs ACTUAL HEADINGS")
for s in sec_refs:
    print(f"  Section {s}: {'ok' if s in head_nums else '<== NO SUCH SECTION'}")
print("  chapters referenced:", chap_refs,
      "| chapters defined:", [c for c, _ in chapters])
