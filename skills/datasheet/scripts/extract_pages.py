"""
Extract text content from specified page ranges of a PDF.
Usage: python extract_pages.py <pdf_path> <page_range> [--detect-images]

Page range format: "5-10" or "5,7,9-12" or "all"

Output JSON structure:
{
  "pdf_path": "...",
  "pages_requested": "5-10",
  "content": [
    {
      "page": 5,
      "text": "...",
      "has_images": true,
      "image_count": 3,
      "text_density": 0.7,
      "needs_multimodal": true
    },
    ...
  ],
  "pages_needing_multimodal": [5, 7]
}
"""
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import fitz


def parse_page_range(range_str: str, total_pages: int) -> list[int]:
    if range_str.lower() == "all":
        return list(range(1, total_pages + 1))

    pages = set()
    parts = range_str.split(",")
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


def analyze_page(page: fitz.Page) -> dict:
    text = page.get_text()
    image_list = page.get_images(full=True)
    image_count = len(image_list)

    page_area = page.rect.width * page.rect.height
    text_blocks = page.get_text("blocks")
    text_area = sum(
        (b[2] - b[0]) * (b[3] - b[1])
        for b in text_blocks
        if b[6] == 0  # text blocks only
    )
    text_density = text_area / page_area if page_area > 0 else 0

    needs_multimodal = (
        (image_count >= 2 and text_density < 0.3)
        or (image_count >= 1 and len(text.strip()) < 100)
        or text_density < 0.15
    )

    return {
        "page": page.number + 1,
        "text": text,
        "has_images": image_count > 0,
        "image_count": image_count,
        "text_density": round(text_density, 3),
        "needs_multimodal": needs_multimodal,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_pages.py <pdf_path> <page_range> [--detect-images]", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    page_range_str = sys.argv[2]
    detect_images = "--detect-images" in sys.argv

    if not pdf_path.exists():
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)

    doc = fitz.open(str(pdf_path))
    pages = parse_page_range(page_range_str, len(doc))

    content = []
    pages_needing_multimodal = []

    for page_num in pages:
        page = doc[page_num - 1]
        if detect_images:
            info = analyze_page(page)
        else:
            info = {
                "page": page_num,
                "text": page.get_text(),
                "has_images": False,
                "image_count": 0,
                "text_density": 1.0,
                "needs_multimodal": False,
            }
        content.append(info)
        if info["needs_multimodal"]:
            pages_needing_multimodal.append(page_num)

    doc.close()

    result = {
        "pdf_path": str(pdf_path),
        "pages_requested": page_range_str,
        "total_pages_extracted": len(content),
        "content": content,
        "pages_needing_multimodal": pages_needing_multimodal,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
