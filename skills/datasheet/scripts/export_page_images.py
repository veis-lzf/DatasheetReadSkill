"""
Export specified PDF pages as PNG images for multimodal analysis.
Usage: python export_page_images.py <pdf_path> <page_list> [--output-dir <dir>] [--dpi <dpi>]

Page list format: "1,3,5-7" or "all"
Default DPI: 200
Default output: ./temp_images/

Output JSON:
{
  "pdf_path": "...",
  "output_dir": "...",
  "dpi": 200,
  "images": [
    {"page": 1, "path": "/path/to/page_001.png", "size_kb": 145},
    ...
  ]
}
"""
import json
import sys
import io
import os
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import fitz


def parse_page_list(page_str: str, total_pages: int) -> list[int]:
    if page_str.lower() == "all":
        return list(range(1, total_pages + 1))

    pages = set()
    parts = page_str.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = max(1, int(start))
            end = min(total_pages, int(end))
            pages.update(range(start, end + 1))
        else:
            p = int(part)
            if 1 <= p <= total_pages:
                pages.add(p)
    return sorted(pages)


def main():
    if len(sys.argv) < 3:
        print("Usage: python export_page_images.py <pdf_path> <page_list> [--output-dir <dir>] [--dpi <dpi>]", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    page_list_str = sys.argv[2]

    output_dir = Path("./temp_images")
    dpi = 200

    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--output-dir" and i + 1 < len(args):
            output_dir = Path(args[i + 1])
            i += 2
        elif args[i] == "--dpi" and i + 1 < len(args):
            dpi = int(args[i + 1])
            i += 2
        else:
            i += 1

    if not pdf_path.exists():
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    pages = parse_page_list(page_list_str, len(doc))

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    images = []
    for page_num in pages:
        page = doc[page_num - 1]
        pix = page.get_pixmap(matrix=matrix)

        filename = f"page_{page_num:04d}.png"
        filepath = output_dir / filename
        pix.save(str(filepath))

        size_kb = os.path.getsize(filepath) / 1024
        images.append({
            "page": page_num,
            "path": str(filepath.resolve()),
            "size_kb": round(size_kb, 1),
        })

    doc.close()

    result = {
        "pdf_path": str(pdf_path),
        "output_dir": str(output_dir.resolve()),
        "dpi": dpi,
        "total_exported": len(images),
        "images": images,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
