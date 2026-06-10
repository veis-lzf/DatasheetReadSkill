# Workflow Guide — IC Datasheet & Schematic Reader

Detailed reference for the datasheet reader skill's internal workflow and script usage.

## Environment Setup

The skill requires a Python virtual environment with PyMuPDF:

```
# First-time setup (run from project root)
python skills/datasheet_reader/scripts/setup_env.py

# Check if environment is ready without modifying anything
python skills/datasheet_reader/scripts/setup_env.py --check-only
```

The venv is created at the project root as `.venv/`. All script invocations use:
- Windows: `.venv\Scripts\python.exe`
- Linux/Mac: `.venv/bin/python`

## Script Calling Conventions

All scripts:
- Accept positional arguments (pdf_path first, then page range/list)
- Output JSON to stdout
- Output errors to stderr
- Return exit code 0 on success, 1 on failure
- Handle missing files gracefully (return JSON with "error" field)

## Processing Strategies by Document Type

### Circuit Schematics (1-10 pages)

Schematics are almost entirely graphical. Text extraction yields minimal useful info (just labels and values scattered across the page). The correct approach:

1. Export ALL pages as images at 200 DPI
2. View each page with multimodal vision
3. Build a mental model of the circuit:
   - Identify all ICs by reference designator (U1, U2, ...)
   - Map passive components (R1=10kΩ, C1=100nF, ...)
   - Trace signal connections between components
   - Identify power rails and their voltages

**Common questions and where to find answers:**
- "What is U1?" → Look at the IC symbol, read the part number printed inside/beside it
- "How is the MCU connected to the sensor?" → Trace nets between the two components
- "What's the decoupling capacitor value?" → Find caps near IC power pins

### Short Datasheets (5-15 pages)

These are typically single-function ICs (op-amps, voltage regulators, simple sensors). They usually contain:
- Page 1: Overview, features, pin diagram
- Pages 2-3: Absolute max ratings, electrical characteristics tables
- Pages 4-8: Typical application circuits, timing diagrams
- Remaining: Package dimensions

Strategy: Export all as images for a complete picture, but also extract text for tables (specs are easier to read as text).

### Long Datasheets (50-500+ pages)

These are complex ICs like microcontrollers (STM32, ESP32, etc.). Structure:
- First pages: Overview, ordering info
- Pin tables: 5-20 pages of pin descriptions
- Memory map: Register addresses and bit fields
- Peripheral chapters: UART, SPI, I2C, ADC, timers, etc.
- Electrical characteristics: DC/AC specs, timing
- Package info: Dimensions, thermal

Strategy: TOC-first navigation is essential. Never try to extract more than 20-30 pages at once.

### Reference Manuals (500-3000+ pages)

Some MCU families have separate reference manuals covering all peripherals in extreme detail. These are the longest documents.

Strategy: Same as long datasheets but even more aggressive about section targeting. The TOC is critical. If no bookmarks exist, the first few pages almost always have a printed table of contents.

## Multimodal Analysis Best Practices

When viewing exported page images:

1. **Timing diagrams**: Look for signal names on the left, timing relationships (setup/hold times), clock edges, and annotated delays.

2. **Block diagrams**: Identify functional blocks, data flow direction (arrows), bus widths, and clock domains.

3. **Pin diagrams**: Match pin numbers to function names. Note alternate functions (AF0, AF1, etc. for STM32).

4. **Application circuits**: Identify the recommended external components and their values. These are reference designs.

5. **Register bit fields**: Tables showing bit positions, names, reset values, and access types (R/W/R-only).

## Navigation Index (`datasheet_index.md`)

When multiple datasheets exist, a centralized navigation index speeds up document targeting:

- **Location**: If all PDFs are in one directory, the index lives in that directory. If PDFs span multiple directories, the index lives at the project root.
- **Content**: Each entry contains the PDF filename, directory, main content summary (IC model, doc type, coverage, key features, page count), and a pointer to the corresponding `_context.md`.
- **Usage**: When the user asks a question without specifying a PDF, read `datasheet_index.md` first to identify the target document, then read that document's `_context.md` for the full TOC.
- **Updates**:
  - Single init (`init`): check if the PDF already has an entry → overwrite or append.
  - Batch init (`init_all`): rewrite the entire index from scratch.

## Handling Edge Cases

### No TOC / No Bookmarks
Run `parse_toc.py` with `--fallback-scan` to attempt page-scanning detection. If that also fails:
1. Extract text from pages 1-5 to find a printed table of contents
2. If no TOC found, extract page 1 for the component overview, then ask the user what they need

### Scanned PDFs (Image-only)
If text extraction returns empty or garbled text for most pages:
- The PDF is likely a scanned document
- Fall back entirely to image export + multimodal
- Process in batches of 5-10 pages to manage context

### Very Large Tables
Some datasheets have tables spanning 10+ pages (e.g., full register maps). For these:
- Extract tables page by page
- Look for the specific register/parameter the user asked about
- Don't try to present the entire table — focus on the relevant rows

### Multiple Documents
If the user provides multiple PDFs (e.g., a datasheet + a schematic):
- Process them independently
- Cross-reference information (e.g., "the schematic uses pin PA5, which according to the datasheet is...")

## Temp File Management

Image exports go to a temp directory. Clean up after answering:
- Default location: `./temp_images/`
- Can be customized with `--output-dir`
- Delete the directory contents after the conversation turn is complete
