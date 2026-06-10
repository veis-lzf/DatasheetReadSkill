"""
Generate raw context data from a PDF for the model to create a _context.md cache file.
Usage: python generate_context.py <pdf_path> [--batch <directory>] [--force]

This script extracts:
1. TOC structure (bookmarks or page-scan fallback)
2. Text from the first few pages (for model to identify IC, doc type, coverage)

It outputs JSON with both pieces of data. The model then reads this output,
uses its understanding to generate the "主要内容" summary, and writes the
final _context.md file.

Output JSON:
{
  "pdf_path": "...",
  "pdf_filename": "...",
  "context_md_path": "...",  // where the _context.md should be saved
  "total_pages": 337,
  "toc_source": "bookmarks",
  "toc": [...],
  "first_pages_text": "...",  // concatenated text from first 2-3 pages
  "existing_context": true/false  // whether _context.md already exists
}
"""
import json
import sys
import io
import re
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


def get_first_pages_text(doc: fitz.Document, max_pages: int = 3) -> str:
    texts = []
    scan_range = min(max_pages, len(doc))
    for i in range(scan_range):
        page = doc[i]
        text = page.get_text()
        if text.strip():
            texts.append(f"--- Page {i+1} ---\n{text}")
    return "\n\n".join(texts)


def process_single_pdf(pdf_path: Path, force: bool = False) -> dict:
    context_name = pdf_path.stem + "_context.md"
    context_path = pdf_path.parent / context_name

    existing = context_path.exists()

    if existing and not force:
        return {
            "pdf_path": str(pdf_path),
            "pdf_filename": pdf_path.name,
            "context_md_path": str(context_path),
            "existing_context": True,
            "skipped": True,
            "message": f"Context file already exists: {context_path}. Use --force to overwrite.",
        }

    doc = fitz.open(str(pdf_path))

    bookmarks = extract_bookmarks(doc)
    if bookmarks:
        toc = bookmarks
        toc_source = "bookmarks"
    else:
        toc = scan_toc_pages(doc)
        toc_source = "page_scan" if toc else "none"

    first_pages_text = get_first_pages_text(doc, max_pages=3)

    result = {
        "pdf_path": str(pdf_path),
        "pdf_filename": pdf_path.name,
        "context_md_path": str(context_path),
        "total_pages": len(doc),
        "toc_source": toc_source,
        "toc": toc,
        "first_pages_text": first_pages_text,
        "existing_context": existing,
        "skipped": False,
    }

    doc.close()
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_context.py <pdf_path> [--batch <directory>] [--force]", file=sys.stderr)
        sys.exit(1)

    force = "--force" in sys.argv
    batch_mode = "--batch" in sys.argv

    if batch_mode:
        batch_idx = sys.argv.index("--batch")
        if batch_idx + 1 >= len(sys.argv):
            print("Error: --batch requires a directory argument", file=sys.stderr)
            sys.exit(1)
        directory = Path(sys.argv[batch_idx + 1])
        if not directory.is_dir():
            print(json.dumps({"error": f"Not a directory: {directory}"}))
            sys.exit(1)

        pdf_files = sorted(directory.glob("*.pdf"))
        results = []
        for pdf_file in pdf_files:
            result = process_single_pdf(pdf_file, force=force)
            results.append(result)

        print(json.dumps({"batch": True, "results": results}, ensure_ascii=False, indent=2))
    else:
        pdf_path = Path(sys.argv[1])
        if not pdf_path.exists():
            print(json.dumps({"error": f"File not found: {pdf_path}"}))
            sys.exit(1)

        result = process_single_pdf(pdf_path, force=force)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
