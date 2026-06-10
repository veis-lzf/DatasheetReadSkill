---
name: datasheet
description: Parse, analyze, and answer questions about IC datasheets (analog ICs, microcontrollers, sensors, etc.) and circuit schematics in PDF format. Use this skill whenever the user provides a datasheet PDF or schematic and asks about electrical characteristics, timing parameters, pinout, register maps, firmware interfaces, component connections, or any technical detail from the document. Also triggers when the user wants to understand a circuit schematic — identifying components, their values, connections, and signal flow. Use even for simple questions like "what's the supply voltage" because the skill handles intelligent page targeting to find the answer efficiently.
---

# IC Datasheet & Schematic Reader

Parse and understand IC datasheets and circuit schematics to answer technical questions accurately.

## Overview

This skill processes PDF documents containing IC datasheets or circuit schematics using a two-path approach:
- **Short documents (≤15 pages)**: Export all pages as images and use multimodal vision to analyze them directly. Ideal for schematics and brief spec sheets.
- **Long documents (>15 pages)**: Parse the table of contents first, locate relevant sections based on the user's question, then extract text and use multimodal vision only for pages with diagrams/figures.

## Interface Specification (工具接口)

When this skill is called by another agent, workflow, or tool chain, use the following contract.

### Input

```
@datasheet_reader(
  action:   "query" | "summarize" | "init" | "init_all" | "list",
  pdf:      "<path>",              // PDF 文件路径（query/summarize/init 必填）
  question: "<string>",            // 问题或总结范围（query 必填，summarize 可选）
  pages:    "<range>",             // 可选，限定页码范围如 "5-10"
  format:   "markdown" | "json"    // 输出格式，默认 "markdown"
)
```

### Actions

| action | 必填参数 | 说明 |
|--------|----------|------|
| `query` | pdf, question | 针对具体问题从 PDF 中提取信息并回答 |
| `summarize` | pdf | 总结文档或指定章节（question 可选，用于限定范围） |
| `init` | pdf | 为指定 PDF 生成/覆写 `_context.md` 缓存，并更新 `datasheet_index.md` 导航文件 |
| `init_all` | — | 批量初始化工作目录下所有 PDF，并重写 `datasheet_index.md` 导航文件 |
| `list` | — | 列出所有已初始化的文档及其主要内容摘要（读取 `datasheet_index.md`） |

### Output

**format = "markdown"（默认）：**

直接返回带引用标注的文本：
```
STM32H750 的 VDD 范围为 1.62~3.6V
[来源: ST-STM32H750VB_2.pdf, 6.3.1 General operating conditions, p.96, Table 22]
```

**format = "json"：**

```json
{
  "status": "ok",
  "action": "query",
  "source_pdf": "ST-STM32H750VB_2.pdf",
  "answer": "STM32H750 的 VDD 范围为 1.62~3.6V",
  "citations": [
    {
      "text": "VDD 供电范围 1.62~3.6V",
      "pdf": "ST-STM32H750VB_2.pdf",
      "section": "6.3.1 General operating conditions",
      "page": 96,
      "detail": "Table 22 第1行"
    }
  ],
  "metadata": {
    "total_pages": 337,
    "sections_consulted": ["6.3.1 General operating conditions"],
    "pages_extracted": [96],
    "multimodal_pages": []
  }
}
```

**错误时：**
```json
{"status": "error", "message": "File not found: ..."}
```

### Calling Examples

```
// 精确问答
@datasheet_reader(action:"query", pdf:"datasheet/ST-STM32H750VB_2.pdf", question:"ADC最大采样率")

// 章节总结
@datasheet_reader(action:"summarize", pdf:"datasheet/UART_spec.pdf", question:"寄存器")

// 指定页码范围查询
@datasheet_reader(action:"query", pdf:"datasheet/rm0433.pdf", question:"USART波特率寄存器", pages:"1850-1860")

// JSON 输出（供下游解析）
@datasheet_reader(action:"query", pdf:"datasheet/ST-STM32H750VB_2.pdf", question:"封装尺寸", format:"json")

// 初始化
@datasheet_reader(action:"init", pdf:"datasheet/new_chip.pdf")

// 列出可用文档
@datasheet_reader(action:"list")
```

---

## Prerequisites

Before first use, set up the Python environment by running:
```
python skills/datasheet_reader/scripts/setup_env.py
```
This creates a `.venv/` with PyMuPDF installed. All subsequent script calls use this venv's Python.

The venv Python path on Windows: `.venv\Scripts\python.exe`

## Workflow

### Step 0: Context Cache — Check or Initialize

Before any PDF processing, check if a cached context file exists:

1. Determine the context file path: `<pdf_directory>/<pdf_stem>_context.md`
   - Example: `datasheet/ST-STM32H750VB_2.pdf` → `datasheet/ST-STM32H750VB_2_context.md`

2. **If `_context.md` exists** → Read it with the Read tool. The file starts with the PDF name and "主要内容" summary, followed by the full TOC. Use this directly — skip PDF TOC parsing entirely.

3. **If `_context.md` does NOT exist** → Generate it:
   ```
   .venv\Scripts\python.exe skills/datasheet_reader/scripts/generate_context.py "<pdf_path>" --force
   ```
   This outputs JSON with the TOC structure and first 2-3 pages of text. Then:
   - Read the JSON output (TOC + first pages text)
   - Using your understanding of the content, identify:
     - IC model number(s) and variants
     - Document type (datasheet / reference manual / programming manual / app note / schematic)
     - Key content areas covered (electrical specs, peripherals, firmware interfaces, etc.)
     - Key peripherals or features listed
   - Write the `_context.md` file using this template:

   ```markdown
   # <PDF filename>

   ## 主要内容

   - **IC型号**: <model numbers and variants>
   - **类型**: <document type>
   - **文档覆盖内容**: <comma-separated list of major topics>
   - **关键外设/特性**: <key peripherals or features>
   - **总页数**: <N>

   ## 目录

   ### <level 1 title> (p.<page>)
   #### <level 2 title> (p.<page>)
   ...
   ```

   **TOC depth rule:** Always include Level 1 and Level 2 entries in the TOC section, regardless of document size. This provides sufficient granularity for precise section targeting.

4. **"初始化" command**: When the user says "初始化 <path>" or "初始化这个数据手册":
   - Run `generate_context.py` with `--force` on the specified PDF
   - Regenerate the `_context.md` (overwrite existing)
   - **Update `datasheet_index.md`** (see Step 0.6)

5. **"全部初始化" command**: When the user says "全部初始化":
   - Run `generate_context.py --batch <datasheet_directory> --force`
   - Process each PDF in the batch output, generate/overwrite all `_context.md` files
   - **Rewrite `datasheet_index.md`** (see Step 0.6)

### Step 0.5: Cross-Document Pre-Analysis（跨文档预分析）

When the user asks about a specific IC or topic (whether or not a specific PDF is given):

> **MANDATORY RULE — Index-First Routing**
>
> You MUST read `datasheet_index.md` **before** reading any `_context.md` file.
> Never skip the index and jump directly to context files.
> The index provides fast document-level routing; the context file provides the detailed TOC for page-level targeting.
> Violating this order (e.g., globbing `_context.md` files directly when an index exists) is not permitted.

> **MANDATORY RULE — Exhaustive Document Routing**
>
> When producing the Document Routing Plan, you MUST evaluate **every** PDF entry in the index for relevance. No entry may be skipped.
> For the following question types, you MUST check whether multiple documents are needed:
> - Questions about "how to configure/use" → require both Reference Manual (registers) + HAL/LL Driver Manual (API)
> - Questions about "electrical characteristics/pins" → require both Datasheet + Reference Manual
> - Questions about "programming model" → require both Programming Manual + Reference Manual
> - Questions about schematic connections → require both Schematic + Datasheet (pin mux)
>
> If the question clearly involves only a single document (e.g., "What is the UART register address?"), selecting one PDF is acceptable, but the routing plan MUST state the exclusion rationale for every omitted document.

#### Phase A: Read Index

1. **Read `datasheet_index.md`** (look in project root first, then in datasheet subdirectories)

#### Phase B: Analyze Relevance for Every PDF Entry

2. **Evaluate each PDF entry in the index** against the user's question:
   - For each PDF, check the IC/Subject, Document Type, Coverage, and Key Features/Peripherals fields
   - Decompose the user's question into multiple dimensions/sub-questions (e.g., "how to configure DMA" involves: hardware functional description, register-level details, HAL API usage, pin assignment, etc.)
   - For each dimension, determine which PDF(s) can provide the relevant information

#### Phase C: Output Document Routing Plan（文档路由计划）

3. **Produce a Document Routing Plan** (internal working document to guide subsequent extraction; not displayed directly to the user):

```
## Document Routing Plan

Question: <user's original question>
Dimension decomposition:
  1. <sub-question/dimension 1> (e.g., hardware functional description)
  2. <sub-question/dimension 2> (e.g., HAL driver API configuration)
  3. ...

| PDF filename | Relevance | Matched dimension | Content to consult | Priority |
|--------------|-----------|-------------------|-------------------|----------|
| rm0433...    | High      | Dimension 1       | DMA register-level description, functional overview | 1 |
| um2217...    | High      | Dimension 2       | HAL DMA/MDMA API interface | 2 |
| ST-STM32H750VB_2... | Low | — | Overview only, not essential | — |
| UART_spec... | None      | —                 | Unrelated to question | — |

Conclusion: N documents required (list filenames)
Exclusion rationale: <brief explanation for each PDF marked "Low" or "None">
```

#### Phase D: Read Context Files and Locate Sections

4. **For all "High relevance" PDFs**, read their `_context.md` (via the `Context File` path in the index) to obtain the full TOC
5. **Locate specific chapters and page ranges from each PDF's TOC**, then consolidate into a unified extraction plan:

```
## Extraction Plan

### PDF 1: rm0433...
- 14.1-14.3 MDMA controller (p.518-524)
- 15.1-15.3 DMA1/DMA2 (p.543-561)
- 16.1-16.3 BDMA (p.575-580)

### PDF 2: um2217...
- 23.1-23.2 HAL DMA Generic Driver (p.338-345)
- 52.1-52.2 HAL MDMA Generic Driver (p.1038-1049)
```

6. Proceed to Step 1+ normal extraction workflow, processing each PDF according to the extraction plan

#### Fallback

**Fallback** (ONLY if `datasheet_index.md` does not exist): Glob all `*_context.md` files and read the header section of each. If this fallback is triggered, recommend the user run `init_all` to generate the index.

### Step 0.6: Navigation Index — `datasheet_index.md`

A centralized index that aggregates paths and main content summaries of all initialized PDFs for fast document targeting.

#### Location Rules

- Scan all directories in the project that contain PDF files
- If all PDFs reside in a single directory → place the index inside that directory (e.g., `datasheet/datasheet_index.md`)
- If PDFs are spread across multiple directories (hierarchical layout) → place the index at the project root (`datasheet_index.md`)

#### File Format

```markdown
# Datasheet Index

> Auto-generated navigation file. Updated on initialization.

## <directory_path>/

### <PDF_filename>
- **IC/Subject**: <model>
- **Document Type**: <type>
- **Coverage**: <topics>
- **Key Features/Peripherals**: <features>
- **Total Pages**: <N>
- **Context File**: <relative path to _context.md>

### <next_PDF_filename>
- ...

## <another_directory>/

### ...
```

#### Updating the Index on Single Init

1. Read the existing `datasheet_index.md` (if present)
2. Search for the PDF's entry by matching `### <filename>`:
   - **Found** → overwrite that entry (from `### <filename>` up to the next `###` or `##`)
   - **Not found** → append the entry under the matching directory group (`## <dir>/`); create the group if it doesn't exist
3. If `datasheet_index.md` itself does not exist → create the file with the header and the new entry

#### Rewriting the Index on Batch Init

1. Iterate over all generated `_context.md` files
2. Extract the "Main Content" section from each (everything before `## 目录` / `## Table of Contents`)
3. Group entries by directory and write the entire `datasheet_index.md` from scratch

### Step 1: Identify Input and Assess Document

When the user provides a PDF path or asks about a datasheet/schematic:

1. If a `_context.md` cache exists (from Step 0), use its TOC and page count directly.
   Otherwise, run the TOC parser:
   ```
   .venv\Scripts\python.exe skills/datasheet_reader/scripts/parse_toc.py "<pdf_path>" --fallback-scan
   ```

2. Based on `total_pages`, choose the processing path:
   - **≤15 pages** → Go to **Short Document Path** (Step 2A)
   - **>15 pages** → Go to **Long Document Path** (Step 2B)

### Step 2A: Short Document Path (Schematics & Brief Specs)

For short documents like circuit schematics, application notes, or brief datasheets:

1. Export all pages as images:
   ```
   .venv\Scripts\python.exe skills/datasheet_reader/scripts/export_page_images.py "<pdf_path>" "all" --output-dir "<temp_dir>" --dpi 200
   ```

2. Use the Read tool to view each exported PNG image. The model's vision capability will interpret:
   - Component symbols and their reference designators (U1, R1, C3, etc.)
   - Component values (resistance, capacitance, IC part numbers)
   - Net connections and signal routing
   - Pin assignments and labels

3. Synthesize the visual information to answer the user's question directly.

**What you can answer in this mode:**
- Which IC corresponds to which reference designator
- Component types and values
- How components are connected (signal flow, power rails, etc.)
- Pin-to-pin connections between ICs
- Power supply topology

### Step 2B: Long Document Path (Datasheets)

For long datasheets (microcontrollers, complex ICs, etc.):

#### Phase 1: Locate Relevant Sections

Using the TOC from Step 1, determine which sections are relevant to the user's question.

**Question-to-section mapping heuristics:**
- Electrical characteristics / absolute max ratings → "Electrical", "DC Characteristics", "Absolute Maximum"
- Timing / clock → "Timing", "Clock", "AC Characteristics"
- Pinout / package → "Pin", "Package", "Ball Map"
- Communication (UART/SPI/I2C) → "UART", "SPI", "I2C", "Serial", "Communication"
- Memory / flash / registers → "Memory", "Flash", "Register Map"
- Power / supply voltage → "Power", "Supply", "Electrical"
- ADC/DAC → "ADC", "DAC", "Analog"
- GPIO → "GPIO", "I/O", "Port"
- Firmware / boot → "Boot", "Firmware", "System"

If the question is ambiguous or broad, present the TOC to the user and ask which section(s) they want to explore.

#### Phase 2: Extract Content

Once target pages are identified, extract text:
```
.venv\Scripts\python.exe skills/datasheet_reader/scripts/extract_pages.py "<pdf_path>" "<page_range>" --detect-images
```

This returns text content plus a list of pages that need multimodal analysis (pages with diagrams, timing charts, block diagrams, etc.).

#### Phase 3: Extract Tables (if relevant)

If the question involves specifications, parameters, or register definitions:
```
.venv\Scripts\python.exe skills/datasheet_reader/scripts/extract_tables.py "<pdf_path>" "<page_range>"
```

#### Phase 4: Multimodal Analysis for Figures

For pages flagged as `needs_multimodal` (timing diagrams, block diagrams, pin diagrams, etc.):
```
.venv\Scripts\python.exe skills/datasheet_reader/scripts/export_page_images.py "<pdf_path>" "<page_list>" --output-dir "<temp_dir>"
```

Then use the Read tool to view these images and extract information that text alone cannot convey.

#### Phase 5: Synthesize Answer

Combine text, tables, and visual information to provide a complete answer.

### Step 3: Interaction Mode (Hybrid)

**Auto-answer** when:
- The question is specific and maps clearly to a section (e.g., "What's the max UART baud rate?")
- The TOC has an obvious matching section
- The extracted content directly answers the question

**Ask the user** when:
- The question is broad (e.g., "Tell me about this chip")
- Multiple sections could be relevant
- The TOC doesn't clearly indicate where to look
- The document has no bookmarks and no detectable TOC structure

When asking, present the document structure concisely:
```
This is a [page_count]-page datasheet for [component]. Here's the structure:
1. Overview (p.1-5)
2. Pin Configuration (p.6-12)
3. Electrical Characteristics (p.13-25)
...
Which section would you like me to focus on?
```

## Script Reference

All scripts are in `skills/datasheet_reader/scripts/` and output JSON to stdout.

| Script | Purpose | Key Args |
|--------|---------|----------|
| `setup_env.py` | Create venv, install deps | `--check-only` |
| `generate_context.py` | Extract TOC + first pages for context cache | `<pdf> [--force] [--batch <dir>]` |
| `parse_toc.py` | Extract PDF outline/TOC | `<pdf> [--fallback-scan]` |
| `extract_pages.py` | Get text from page range | `<pdf> <range> [--detect-images]` |
| `export_page_images.py` | Render pages as PNG | `<pdf> <pages> [--output-dir] [--dpi]` |
| `extract_tables.py` | Extract tables as markdown | `<pdf> <range>` |

Page range format: `"5-10"`, `"1,3,5-7"`, or `"all"`

## Output Format & Citation Rules

Every piece of information you extract or present must carry a source citation so the user can verify it against the original PDF. This is non-negotiable — traceability is critical for hardware engineering work where a wrong value can damage circuits.

### Citation Format

Use inline citation markers after each information point:

```
[来源: <PDF文件名>, <章节号> <章节名>, p.<页码>]
```

**Extended citation for specific content types:**

| Content Type | Citation Suffix | Example |
|---|---|---|
| List item | `第N点` | `[来源: UART_spec.pdf, 5.1 Initialization, p.17, 第3点]` |
| Table cell | `Table N 第M行` | `[来源: ST-STM32H750VB_2.pdf, 6.2 Absolute maximum ratings, p.94, Table 19 第2行]` |
| Figure/diagram | `Figure N "<描述部分>"` | `[来源: ST-STM32H750VB_2.pdf, 6.1.6 Power supply scheme, p.93, Figure 11 "VDD domain"部分]` |
| Formula | `公式N` or description | `[来源: UART_spec.pdf, 5.1 Initialization, p.18, 波特率公式]` |
| Schematic (no chapters) | page only | `[来源: board_v2.pdf, p.3]` |
| Register bit field | `Register <name> bit <N>` | `[来源: UART_spec.pdf, 4.5 Line Control Register, p.12, LCR bit 7]` |

### Output Mode 1: Q&A (Default)

When answering a specific question, attach citations to each key fact:

```
STM32H750VB 的 VDD 供电范围为 1.7V ~ 3.6V
[来源: ST-STM32H750VB_2.pdf, 6.3.1 General operating conditions, p.96, Table 22 第1行]

复位后 UART 默认配置为 8 位数据、无校验、1 停止位
[来源: UART_spec.pdf, 5.1 Initialization, p.17, 第4点]
```

Group related facts together but ensure each distinct claim has its own citation. If multiple facts come from the same source location, they can share one citation at the end of the group.

### Output Mode 2: Summary (总结模式)

When the user asks to "summarize" a document, chapter, or section, output a structured markdown document:

```markdown
# <PDF文件名> — <总结范围> 总结

## 概述
<该部分的功能定位和核心用途>
[来源: <PDF>, <章节>, p.<页码>]

## 详细内容

### <子章节标题1>
<详细解释，每个关键点附带引用>
[来源: ...]

### <子章节标题2>
...

## 关键参数表
| 参数 | 值 | 单位 | 条件 | 来源 |
|------|-----|------|------|------|
| VDD | 1.7~3.6 | V | - | [来源: ..., p.96, Table 22] |

## 相关图表
- Figure 11: Power supply scheme — 展示了各电源域的层级关系和推荐去耦电容值 [来源: ..., p.93, Figure 11]
- Figure 12: Current consumption measurement [来源: ..., p.94, Figure 12]
```

### Output Mode 3: Pipeline (工具链模式)

When this skill is invoked as part of a larger tool pipeline (another agent or workflow calls it):

**Detection**: If the calling context specifies an output schema, JSON format requirement, or structured field names, switch to pipeline mode.

**Output structure**:
```json
{
  "query": "<the question asked>",
  "source_pdf": "<filename>",
  "answer": "<the synthesized answer text>",
  "citations": [
    {
      "text": "<the specific claim>",
      "pdf": "<filename>",
      "section": "<chapter number and name>",
      "page": <page_number>,
      "detail": "<table/figure/list item specifics>"
    }
  ],
  "metadata": {
    "total_pages": 337,
    "sections_consulted": ["6.3.1 General operating conditions"],
    "pages_extracted": [96, 97],
    "multimodal_pages": []
  }
}
```

If no specific format is requested by the caller, use the default markdown + citation format (Mode 1 or Mode 2 depending on the task).

### How to Track Citations During Extraction

While processing content from scripts, maintain a mental mapping:
1. The `parse_toc.py` output gives you chapter numbers and names for each page range
2. The `extract_pages.py` output includes the page number for each text block
3. The `extract_tables.py` output includes page number and table index
4. For multimodal pages, note the page number and any figure/table labels visible in the image

When synthesizing your answer, cross-reference each fact with the page it came from, then look up which TOC entry covers that page to get the chapter number and name.

## Important Notes

- Keep extracted page ranges focused. For a 1000-page datasheet, extract 10-20 pages at a time, not hundreds.
- When text extraction gives garbled results (common with scanned PDFs), fall back to image export + multimodal for those pages.
- Tables in datasheets often contain critical specs. Prefer table extraction over raw text for parameter values.
- For timing diagrams and waveforms, image mode is essential — text extraction cannot capture these.
- Clean up temp_images directory after answering to avoid accumulating files.
- If the venv doesn't exist yet, run setup_env.py first before any other script.
