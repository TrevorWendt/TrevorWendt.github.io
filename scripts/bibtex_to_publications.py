#!/usr/bin/env python3
import os, re, sys, pathlib, shutil
from datetime import datetime
import bibtexparser
from slugify import slugify

ROOT = pathlib.Path(__file__).resolve().parents[1]
BIB = ROOT / "data" / "bibliography" / "publications.bib"
OUTDIR = ROOT / "content" / "publication"

def first(values):
    if isinstance(values, list) and values:
        return values[0]
    return values

def parse_date(year, month=None, day=None):
    y = str(year).strip() if year else "1900"
    m = (str(month).strip() if month else "01").zfill(2)
    d = (str(day).strip() if day else "01").zfill(2)
    # Ensure valid fallback
    m = "01" if not m.isdigit() else m
    d = "01" if not d.isdigit() else d
    return f"{y}-{m}-{d}"

def split_authors(author_field):
    if not author_field:
        return []
    # BibTeX authors generally separated by ' and '
    parts = [a.strip() for a in re.split(r"\s+and\s+", author_field)]
    return [re.sub(r"\s+", " ", p) for p in parts if p]

def yaml_escape(s):
    if s is None:
        return ""
    s = str(s)
    if any(ch in s for ch in [":","{","}","[","]","-","#","&","*","!","|",">","'","\"","%","@","`"]):
        # Use pipe literal block for long/complex strings
        if "\n" in s or len(s) > 80:
            return "|\n  " + "\n  ".join(s.splitlines())
        return f"\"{s.replace('\"','\\\"')}\""
    return s

def write_markdown(entry):
    # Basic fields
    title = entry.get("title", "").strip().strip("{}")
    authors = split_authors(entry.get("author", ""))

    year = entry.get("year")
    month = entry.get("month")
    day = entry.get("day")
    date = parse_date(year, month, day)

    container = entry.get("journal") or entry.get("booktitle") or ""
    doi = entry.get("doi", "").strip()
    url = entry.get("url", "").strip()
    abstract = entry.get("abstract", "").strip()

    # Publication type mapping to Wowchemy (2=journal, 1=conf)
    pubtype = "2" if entry.get("journal") else ("1" if entry.get("booktitle") else "0")

    # Slug
    key = entry.get("ID") or slugify(title) or f"paper-{datetime.now().timestamp()}"
    slug = slugify(key)

    # Dir
    pdir = OUTDIR / slug
    if pdir.exists():
        shutil.rmtree(pdir)
    pdir.mkdir(parents=True, exist_ok=True)

    # Front matter
    fm = []
    fm.append("---")
    fm.append(f"title: {yaml_escape(title) if title else 'Untitled'}")
    if authors:
        fm.append("authors:")
        for a in authors:
            fm.append(f"  - {yaml_escape(a)}")
    fm.append(f"date: {date}")
    fm.append(f"publication_types: [\"{pubtype}\"]")
    if container:
        fm.append(f"publication: {yaml_escape('*' + container + '*')}")
    if doi:
        fm.append(f"doi: \"{doi}\"")
    if url:
        fm.append(f"url_source: \"{url}\"")
    if abstract:
        fm.append(f"abstract: {yaml_escape(abstract)}")
    # Raw BibTeX (optional, useful)
    bib_block = entry.get("raw", "").strip()
    if bib_block:
        fm.append("bibtex: |")
        for line in bib_block.splitlines():
            fm.append(f"  {line}")
    fm.append("---\n")

    (pdir / "index.md").write_text("\n".join(fm), encoding="utf-8")

def main():
    if not BIB.exists():
        print(f"BibTeX not found at {BIB}", file=sys.stderr)
        sys.exit(0)

    OUTDIR.mkdir(parents=True, exist_ok=True)

    with open(BIB, "r", encoding="utf-8") as f:
        db = bibtexparser.load(f)

    # Preserve original BibTeX block for each entry (nice to keep)
    raw_txt = BIB.read_text(encoding="utf-8")
    # naive split by '@' to capture raw; rebuild map by ID if possible
    raw_entries = {}
    for chunk in re.split(r"(?=@)", raw_txt):
        m = re.search(r"@(\w+)\s*{\s*([^,]+),", chunk)
        if m:
            raw_entries[m.group(2).strip()] = chunk.strip()

    for e in db.entries:
        e["raw"] = raw_entries.get(e.get("ID",""), "")
        write_markdown(e)

    print(f"Imported {len(db.entries)} entries to {OUTDIR}")

if __name__ == "__main__":
    main()
