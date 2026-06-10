"""
Extract tables from specified PDF pages and output as markdown.
Usage: python extract_tables.py <pdf_path> <page_range>

Page range format: "5-10" or "5,7,9-12"

Output JSON:
{
  "pdf_path": "...",
  "tables": [
    {
      "page": 5,
      "table_index": 0,
      "rows": 10,
      "cols": 4,
      "markdown": "| Col1 | Col2 | ... |\n|---|---| ... |..."
    },
    ...
  ]
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


def table_to_markdown(table_data: list[list]) -> str:
    if not table_data or not table_data[0]:
        return ""

    def clean_cell(cell):
        if cell is None:
            return ""
        return str(cell).replace("|", "\\|").replace("\n", " ").strip()

    header = table_data[0]
    cols = len(header)

    lines = []
    header_cells = [clean_cell(c) for c in header]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("| " + " | ".join(["---"] * cols) + " |")

    for row in table_data[1:]:
        row_cells = [clean_cell(c) for c in row]
        while len(row_cells) < cols:
            row_cells.append("")
        lines.append("| " + " | ".join(row_cells[:cols]) + " |")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_tables.py <pdf_path> <page_range>", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    page_range_str = sys.argv[2]

    if not pdf_path.exists():
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)

    doc = fitz.open(str(pdf_path))
    pages = parse_page_range(page_range_str, len(doc))

    tables = []
    for page_num in pages:
        page = doc[page_num - 1]
        try:
            page_tables = page.find_tables()
            for idx, table in enumerate(page_tables):
                data = table.extract()
                if data and len(data) > 1:
                    md = table_to_markdown(data)
                    tables.append({
                        "page": page_num,
                        "table_index": idx,
                        "rows": len(data),
                        "cols": len(data[0]) if data else 0,
                        "markdown": md,
                    })
        except Exception:
            pass

    doc.close()

    result = {
        "pdf_path": str(pdf_path),
        "pages_scanned": len(pages),
        "tables_found": len(tables),
        "tables": tables,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
