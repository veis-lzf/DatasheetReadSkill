"""
Parse PDF table of contents (bookmarks/outline) and output as JSON.
Usage: python parse_toc.py <pdf_path> [--fallback-scan]

Output JSON structure:
{
  "pdf_path": "...",
  "total_pages": 123,
  "has_bookmarks": true,
  "toc": [
    {"level": 1, "title": "Chapter 1", "page": 5},
    {"level": 2, "title": "1.1 Overview", "page": 5},
    ...
  ]
}
"""
import json
import sys
import re
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import fitz


def extract_bookmarks(doc: fitz.Document) -> list[dict]:
    toc = doc.get_toc(simple=True)
    entries = []
    for level, title, page in toc:
        entries.append({
            "level": level,
            "title": title.strip(),
            "page": page,
        })
    return entries


def scan_toc_pages(doc: fitz.Document, max_scan_pages: int = 10) -> list[dict]:
    """Fallback: scan first pages for table-of-contents-like content."""
    toc_patterns = [
        re.compile(r"^(.+?)\s*[\.·…]{3,}\s*(\d+)\s*$", re.MULTILINE),
        re.compile(r"^(\d+[\.\d]*)\s+(.+?)\s+(\d+)\s*$", re.MULTILINE),
        re.compile(r"^(第.+?[章节])\s+(.+?)\s*[\.·…]*\s*(\d+)\s*$", re.MULTILINE),
    ]

    entries = []
    scan_range = min(max_scan_pages, len(doc))

    for page_idx in range(scan_range):
        page = doc[page_idx]
        text = page.get_text()

        for pattern in toc_patterns:
            matches = pattern.findall(text)
            if len(matches) >= 3:
                for match in matches:
                    if len(match) == 2:
                        title, page_num = match
                        entries.append({
                            "level": 1,
                            "title": title.strip(),
                            "page": int(page_num),
                        })
                    elif len(match) == 3:
                        section_num, title, page_num = match
                        level = section_num.count(".") + 1 if "." in section_num else 1
                        entries.append({
                            "level": level,
                            "title": f"{section_num} {title}".strip(),
                            "page": int(page_num),
                        })

        if entries:
            break

    seen = set()
    unique_entries = []
    for e in entries:
        key = (e["title"], e["page"])
        if key not in seen:
            seen.add(key)
            unique_entries.append(e)

    return unique_entries


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_toc.py <pdf_path> [--fallback-scan]", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    fallback_scan = "--fallback-scan" in sys.argv

    if not pdf_path.exists():
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)

    doc = fitz.open(str(pdf_path))

    bookmarks = extract_bookmarks(doc)

    result = {
        "pdf_path": str(pdf_path),
        "total_pages": len(doc),
        "has_bookmarks": len(bookmarks) > 0,
        "toc": bookmarks,
    }

    if not bookmarks and fallback_scan:
        scanned = scan_toc_pages(doc)
        result["toc"] = scanned
        result["toc_source"] = "page_scan"
    elif bookmarks:
        result["toc_source"] = "bookmarks"
    else:
        result["toc_source"] = "none"

    doc.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
