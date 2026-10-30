---
name: requirements-document
description: "Use this skill whenever the user asks to create a requirements document, PRD, business requirements document, or product requirements document for any project. Triggers include: 'create a requirements doc', 'write a PRD', 'make a requirements document for [project name]', 'turn this into a requirements doc', or any request to produce a formal Word document listing what a system must do. This skill produces a fully formatted .docx (plus PDF preview) that exactly matches the MHK Tech Inc. house style used across the CEO, SOS, and COI projects — cover page, metadata, live TOC, styled headings, requirement lines, tables, header and footer."
---

# Requirements Document — MHK Tech House Style

Produces a polished `.docx` + `.pdf` from any project description. The output is always the same structure, the same colours, the same fonts, and the same section order — only the content changes per project.

---

## Step 0 — Read this before writing a single line

- `docx` is **preinstalled**. `require('docx')` directly. Do NOT run `npm install`.
- Never use `\n` inside a `TextRun` — use separate `Paragraph` elements.
- Never insert `•` literally — use `bullet: { level: 0 }` on a `Paragraph`.
- `PageBreak` must be inside a `Paragraph`.
- Table shading: always `ShadingType.CLEAR`, never `SOLID`.
- Tables need `columnWidths` on the `Table` AND `width` on every `TableCell`, both in `WidthType.PERCENTAGE`. Column widths must sum to 100.
- Bookmarks: use `new Bookmark({ id, name, children: [...runs] })` — **never** `BookmarkStart`/`BookmarkEnd` directly; those emit `[object Object]` as the name.
- `PageReference(bmId)` emits a live PAGEREF field. The `bmId` string must exactly match the `id` and `name` passed to `Bookmark`.
- Page size is **US Letter**: `{ width: 12240, height: 15840 }` (DXA).
- Verify output: convert to PDF and read every page before presenting.

---

## Step 1 — Gather content from the user

Before writing any code, extract or ask for:

| Item | Where it comes from |
|---|---|
| Project / system name | User prompt or uploaded doc |
| Document type label | "Product Requirements Document (PRD)" unless user says otherwise |
| Status | e.g. "Active — In Development" |
| Date | Current month + year |
| Author | Ask if unknown (default: Jyothirmai Chandolu for MHK projects) |
| Organization | MHK Tech Inc. (default) |
| Version | "1.0" unless user says otherwise |
| All 11 section contents | Derive from project description; ask if ambiguous |

---

## Step 2 — Fixed document structure (never change the order)

Every requirements document has exactly these 11 numbered sections. Add subsections as needed; never remove a section entirely — write "Not applicable for this project." if a section has nothing.

```
1.  Summary
2.  Problem Statement
    2.1  Gaps in Existing Approaches
    2.2  The Core Gap
3.  Mission and Vision
    Mission
    Vision
4.  Goals
5.  Objectives
    (subsections named by theme, e.g. Data Extraction / Data Quality / Platform / Security)
6.  Scope
    In Scope
    Out of Scope
7.  Target Users          ← always a table
8.  Functional Requirements
    8.1 … 8.N            ← one subsection per feature area; each item is FR-NN:
9.  Non-Functional Requirements
    9.1 Performance
    9.2 Reliability
    9.3 Data Accuracy
    9.4 Scalability
    9.5 Security
    9.6 Maintainability
    9.7 Cost Efficiency   ← each item is NFR-NN:
10. Assumptions
11. Constraints
    11.1 Data Source Constraints
    11.2 Infrastructure Constraints
    11.3 AI Model Constraints
    11.4 Budget Constraints
```

---

## Step 3 — Colour palette and typography (exact values — do not change)

```js
const C_NAVY  = '1F3864';   // H1 text, cover title, metadata values, FR/NFR labels
const C_BLUE  = '2E5496';   // H2 text, borders/rules, TOC L2 entries, header text, metadata labels
const C_GRAY  = '595959';   // TOC page numbers, footer page number, cover sub-labels
const C_WHITE = 'FFFFFF';   // table header text, cell fill
const C_SHADE = 'E8EAF6';   // alternating metadata + table row shading
const C_BODY  = '2B2B2B';   // all body paragraph text
const C_DKGRAY= '333333';   // table body cell text

const FONT  = 'Arial';      // headings, cover, metadata labels, TOC, header, footer
const FBODY = 'Calibri';    // all body paragraphs, bullets, requirement lines, table body

const LINE_SPACING = { line: 259, lineRule: LineRuleType.AUTO };
```

---

## Step 4 — Paragraph helpers (copy verbatim into every build script)

```js
// ── H1: dark navy, 15pt Arial bold, blue bottom border ───────────────
const h1 = (text, bmId) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [
    new Bookmark({ id: bmId, name: bmId,
      children: [new TextRun({ text, font: FONT, size: 30, bold: true, color: C_NAVY })] }),
  ],
  border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C_BLUE, space: 6 } },
  spacing: { before: 400, after: 160 },
});

// ── H2: blue, 12pt Arial bold, no border ─────────────────────────────
const h2 = (text, bmId) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [
    new Bookmark({ id: bmId, name: bmId,
      children: [new TextRun({ text, font: FONT, size: 24, bold: true, color: C_BLUE })] }),
  ],
  spacing: { before: 280, after: 100 },
});

// ── Body paragraph: Calibri 11pt ─────────────────────────────────────
const body = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, font: FBODY, size: 22, color: C_BODY })],
  spacing: { before: opts.before ?? 0, after: opts.after ?? 160, ...LINE_SPACING },
  alignment: opts.align || AlignmentType.LEFT,
});

// ── Bullet: pass string or array of TextRun for mixed bold/plain ──────
const bullet = (runs) => {
  const children = typeof runs === 'string'
    ? [new TextRun({ text: runs, font: FBODY, size: 22, color: C_BODY })]
    : runs;
  return new Paragraph({
    children,
    bullet: { level: 0 },
    spacing: { before: 40, after: 80, ...LINE_SPACING },
  });
};

// ── Requirement line: "FR-NN:" bold navy + body text ─────────────────
// Handles both FR-NN: and NFR-NN: prefixes automatically
const req = (text) => {
  const m = text.match(/^((?:FR|NFR)-\d+:)\s*([\s\S]*)$/);
  if (!m) return bullet(text);
  return new Paragraph({
    children: [
      new TextRun({ text: m[1] + ' ', font: FBODY, size: 22, bold: true, color: C_NAVY }),
      new TextRun({ text: m[2],       font: FBODY, size: 22, color: C_BODY }),
    ],
    bullet: { level: 0 },
    spacing: { before: 40, after: 80, ...LINE_SPACING },
  });
};

// ── Empty spacer ──────────────────────────────────────────────────────
const sp = (before = 0, after = 160) =>
  new Paragraph({ children: [], spacing: { before, after } });

// ── TOC entry: dot-leader tab → live PageReference ───────────────────
// level 1 = section (navy bold 11pt)   level 2 = subsection (blue 10pt indented)
const tocEntry = (label, bmId, level) => {
  const sz   = level === 1 ? 22 : 20;
  const col  = level === 1 ? C_NAVY : C_BLUE;
  const bold = level === 1;
  const left = level === 1 ? 0 : convertInchesToTwip(0.35);
  return new Paragraph({
    tabStops: [{ type: TabStopType.RIGHT, position: 8640, leader: 'dot' }],
    indent:   { left, hanging: 0 },
    spacing:  { before: 28, after: 28 },
    children: [
      new TextRun({ text: label, font: FONT, size: sz, bold, color: col }),
      new TextRun({ text: '\t',  font: FONT, size: sz }),
      new PageReference(bmId, { font: FONT, size: sz, color: C_GRAY }),
    ],
  });
};
```

---

## Step 5 — Table helper (Target Users and any other 2-column table)

```js
// Navy header row + alternating E8EAF6 / white body rows
// widths: array of column widths as percentages, must sum to 100
const mkCell = (text, opts = {}) => new TableCell({
  children: [new Paragraph({
    children: [new TextRun({ text, font: FBODY, size: opts.sz || 20,
      bold: opts.bold || false, color: opts.color || C_DKGRAY })],
    spacing: { before: 80, after: 80 },
    indent: { left: 80 },
  })],
  shading: opts.fill
    ? { fill: opts.fill, type: ShadingType.CLEAR, color: 'auto' }
    : undefined,
  borders: {
    top:    { style: BorderStyle.SINGLE, size: 4, color: 'C5CAE9' },
    bottom: { style: BorderStyle.SINGLE, size: 4, color: 'C5CAE9' },
    left:   { style: BorderStyle.SINGLE, size: 4, color: 'C5CAE9' },
    right:  { style: BorderStyle.SINGLE, size: 4, color: 'C5CAE9' },
  },
  width: { size: opts.w || 50, type: WidthType.PERCENTAGE },
});

const hdrCell = (text, w) => new TableCell({
  children: [new Paragraph({
    children: [new TextRun({ text, font: FONT, size: 20, bold: true, color: C_WHITE })],
    spacing: { before: 80, after: 80 },
    indent: { left: 80 },
  })],
  shading: { fill: C_NAVY, type: ShadingType.CLEAR, color: 'auto' },
  borders: {
    top:    { style: BorderStyle.SINGLE, size: 4, color: C_NAVY },
    bottom: { style: BorderStyle.SINGLE, size: 4, color: C_NAVY },
    left:   { style: BorderStyle.SINGLE, size: 4, color: C_NAVY },
    right:  { style: BorderStyle.SINGLE, size: 4, color: C_NAVY },
  },
  width: { size: w, type: WidthType.PERCENTAGE },
});

const table2 = (headers, rows, widths = [30, 70]) => new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  rows: [
    new TableRow({
      children: headers.map((h, i) => hdrCell(h, widths[i])),
      tableHeader: true,
    }),
    ...rows.map((r, ri) => new TableRow({
      children: r.map((v, ci) => mkCell(v, {
        fill: ri % 2 === 0 ? C_SHADE : C_WHITE,
        w: widths[ci],
      })),
    })),
  ],
  columnWidths: widths.map(w => Math.round(w * 9360 / 100)),
});
```

---

## Step 6 — Three-section document layout (cover / meta+TOC / content)

The document always has exactly **three Word sections**:

| Section | Pages | Header | Footer | Page numbers |
|---|---|---|---|---|
| 1 — Cover | 1 page | None | None | Not shown |
| 2 — Metadata + TOC | 1–2 pages | None | None | Not shown |
| 3 — Content | All remaining | Right-aligned, blue, Arial 9pt | Centered page number, Arial 9pt | Starts at 1 |

### Cover page children

```js
const coverChildren = [
  sp(1800, 0),
  // Line 1 of title (project name)
  new Paragraph({
    children: [new TextRun({ text: PROJECT_NAME, font: FONT, size: 56, bold: true, color: C_NAVY })],
    spacing: { before: 0, after: 60 },
  }),
  // Line 2 of title ("Requirements Document")
  new Paragraph({
    children: [new TextRun({ text: 'Requirements Document', font: FONT, size: 56, bold: true, color: C_NAVY })],
    spacing: { before: 0, after: 200 },
  }),
  // Decorative blue rule
  new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 16, color: C_BLUE, space: 8 } },
    spacing: { before: 80, after: 200 },
    children: [],
  }),
  // Document type label
  new Paragraph({
    children: [new TextRun({ text: DOC_TYPE_LABEL, font: FONT, size: 22, bold: true, color: C_BLUE })],
    spacing: { before: 80, after: 60 },
  }),
  // Date · Version
  new Paragraph({
    children: [new TextRun({ text: `${DATE}  ·  Version ${VERSION}`, font: FONT, size: 20, color: C_GRAY })],
    spacing: { before: 40, after: 0 },
  }),
  sp(1600, 0),
];
```

### Metadata page children

```js
const META_ROWS = [
  ['Document Title',  FULL_DOC_TITLE],
  ['Version',         VERSION],
  ['Status',          STATUS],
  ['Date',            DATE],
  ['Author',          AUTHOR],
  ['Organization',    ORGANIZATION],
  ['Document Type',   DOC_TYPE_LABEL],
];

const metaChildren = [
  new Paragraph({
    children: [new TextRun({ text: 'Document Information', font: FONT, size: 30, bold: true, color: C_NAVY })],
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C_BLUE, space: 6 } },
    spacing: { before: 360, after: 200 },
  }),
  ...META_ROWS.map(([label, value], i) => new Paragraph({
    children: [
      new TextRun({ text: label + ':   ', font: FBODY, size: 20, bold: true,  color: C_BLUE }),
      new TextRun({ text: value,          font: FBODY, size: 20, bold: false, color: C_NAVY }),
    ],
    shading: { fill: i % 2 === 0 ? C_SHADE : C_WHITE, type: ShadingType.CLEAR, color: 'auto' },
    indent: { left: 240, right: 240 },
    spacing: { before: 120, after: 120 },
  })),
  sp(200, 0),
];
```

### TOC heading paragraph

```js
new Paragraph({
  children: [new TextRun({ text: 'Table of Contents', font: FONT, size: 30, bold: true, color: C_NAVY })],
  border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C_BLUE, space: 6 } },
  spacing: { before: 0, after: 160 },
})
```

Then add one `tocEntry(label, bmId, level)` call per section and subsection, followed by `sp(120, 0)`.

### Header and footer (content section only)

```js
const docHeader = new Header({
  children: [new Paragraph({
    children: [new TextRun({
      text: `${PROJECT_NAME} — Requirements Document`,
      font: FONT, size: 18, color: C_BLUE,
    })],
    alignment: AlignmentType.RIGHT,
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C_BLUE, space: 4 } },
  })],
});

const docFooter = new Footer({
  children: [new Paragraph({
    children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: C_GRAY })],
    alignment: AlignmentType.CENTER,
    border: { top: { style: BorderStyle.SINGLE, size: 6, color: C_BLUE, space: 4 } },
  })],
});
```

### Document assembly

```js
const doc = new Document({
  numbering: { config: [{
    reference: 'bullets',
    levels: [{
      level: 0,
      format: LevelFormat.BULLET,
      text: '\u2022',
      alignment: AlignmentType.LEFT,
      style: {
        paragraph: { indent: { left: convertInchesToTwip(0.35), hanging: convertInchesToTwip(0.2) } },
        run: { font: 'Symbol', size: 22 },
      },
    }],
  }] },
  sections: [
    // ── Section 1: Cover (no header/footer) ──────────────────────
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1728, bottom: 1440, left: 1728 },
        },
        type: SectionType.NEXT_PAGE,
      },
      children: coverChildren,
    },
    // ── Section 2: Metadata + TOC (no header/footer) ──────────────
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1728, bottom: 1440, left: 1728 },
        },
        type: SectionType.NEXT_PAGE,
      },
      children: [...metaChildren, ...tocChildren],
    },
    // ── Section 3: Content (header + footer, page restart at 1) ───
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1728, bottom: 1080, left: 1728 },
          pageNumbers: { start: 1 },
        },
        type: SectionType.NEXT_PAGE,
      },
      headers: { default: docHeader },
      footers: { default: docFooter },
      children: content,
    },
  ],
});

Packer.toBuffer(doc).then(buf => {
  require('fs').writeFileSync('/home/claude/OUTPUT_FILENAME.docx', buf);
  console.log('Written:', buf.length, 'bytes');
});
```

---

## Step 7 — Section-by-section writing rules

### Section 1 — Summary
One to four `body()` paragraphs. Must answer: what does this system do, what problem does it solve, what does it produce, and what technology does it run on today? Use mixed `TextRun` arrays inside a `Paragraph` to bold key terms (e.g. product name, direction labels).

### Section 2 — Problem Statement
Opening `body()` paragraph sets the business context. Then `h2('2.1 Gaps in Existing Approaches', ...)` followed by `bullet()` calls — each gap uses a bold prefix run + plain continuation run:
```js
bullet([
  new TextRun({ text: 'The gap name', font: FBODY, size: 22, bold: true, color: C_BODY }),
  new TextRun({ text: ' description of the gap...', font: FBODY, size: 22, color: C_BODY }),
])
```
Then `h2('2.2 The Core Gap', ...)` + one `body()` paragraph that names the exact gap this project fills.

### Section 3 — Mission and Vision
`h2('Mission', 'SMission')` + one `body()`. `h2('Vision', 'SVision')` + one `body()`. Mission = what the system does operationally. Vision = what it becomes as the authoritative source.

### Section 4 — Goals
Flat list of `bullet()` calls. Each goal is one sentence starting with a verb (Extract / Track / Automatically / Guarantee / Let / Keep). Typically 5–8 goals.

### Section 5 — Objectives
Group into themed `h2()` subsections (e.g. Data Extraction, Data Quality, Platform, Security and Automation — adapt names to the project). Each subsection has 2–4 `bullet()` calls. Objectives are more specific than Goals — each should be measurable or verifiable.

### Section 6 — Scope
`h2('In Scope', ...)` — bullet list of everything the system handles. `h2('Out of Scope', ...)` — bullet list of what is explicitly excluded. Out of Scope entries often mirror In Scope limitations (e.g. "non-standard forms", "multi-tenant", "mobile app", "AI/LLM in the core path").

### Section 7 — Target Users
Always a `table2()` with headers `['User Type', 'How They Use the Platform']` and column widths `[30, 70]`. Typical rows: Internal staff, the primary external actor (vendor / agent / client / researcher), Administrator. Add rows for any role that interacts with the system differently.

### Section 8 — Functional Requirements
One `h2()` per feature area. Under each `h2()`, one `req()` call per requirement. Requirements are numbered sequentially across the whole section: `FR-01:`, `FR-02:`, … `FR-NN:`. Each requirement:
- Starts with "System must …" or "Backend must …" — active voice, specific
- Names what the behaviour is, not how it is implemented
- Is atomic — one thing per requirement

### Section 9 — Non-Functional Requirements
Fixed seven `h2()` subsections (9.1–9.7). Under each, two `req()` calls with `NFR-NN:` prefix. Keep NFRs measurable where possible (e.g. "must respond in under X seconds", "must be safe to re-run without duplicates").

### Section 10 — Assumptions
Flat `bullet()` list, 4–6 items. Each assumption is a condition the system relies on being true that is outside the system's control (e.g. data quality of inputs, user behaviour, external service availability).

### Section 11 — Constraints
Four fixed `h2()` subsections. Each has 2–3 `bullet()` calls describing a hard limit the system cannot change, organized by type: data sources, infrastructure, AI/model usage, budget.

---

## Step 8 — Bookmark ID conventions

Use short, stable, all-caps alphanumeric IDs. The `id`, `name`, and the `bmId` passed to `tocEntry()` must all be the same string.

```
S1   S2   S21  S22  S3   S4   S5   S6   S7   S8   S9   S10  S11
SMission  SVision
S5DE S5DQ S5PL S5SA          ← Objectives subsections (adapt names)
S81  S82  S83  … S8N         ← FR subsections (number sequentially)
S91  S92  S93  S94  S95  S96  S97
S111 S112 S113 S114
SInScope  SOutScope
```

---

## Step 9 — Required imports (top of every build script)

```js
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  TableRow, TableCell, Table, WidthType, ShadingType, BorderStyle,
  PageNumber, Header, Footer, TabStopType,
  LevelFormat, convertInchesToTwip, PageReference,
  Bookmark, LineRuleType, SectionType,
} = require('docx');
const fs = require('fs');
```

---

## Step 10 — Verify and deliver

```bash
# Run the build script
node /home/claude/build_PROJECT.js

# Convert to PDF
python /mnt/skills/public/docx/scripts/office/soffice.py \
  --headless --convert-to pdf /home/claude/PROJECT.docx --outdir /home/claude/

# Render every page and read each image before presenting
pdfinfo /home/claude/PROJECT.pdf | grep Pages
pdftoppm -jpeg -r 130 /home/claude/PROJECT.pdf /home/claude/pg
# Then: view /home/claude/pg-01.jpg through pg-NN.jpg
```

**Check on every page before presenting:**
- Page 1: Cover — large navy title, blue rule, blue doc-type label, grey date·version. No header or footer.
- Page 2: Metadata rows alternating `E8EAF6`/white + "Table of Contents" heading + all TOC entries with dot leaders and live page numbers. No header or footer.
- Page 3+: Right-aligned blue header with bottom rule. Centered grey page number with top rule. H1 dark navy with bottom border. H2 blue, no border. Bullets indented 0.35″. `FR-NN:` labels bold navy. Table rows alternating.

Copy both files to `/mnt/user-data/outputs/` and call `present_files`.

---

## Quick-reference: what varies per project vs what never changes

| Always the same | Changes per project |
|---|---|
| Colour palette (all 7 hex values) | Project name (cover title line 1) |
| Font stack (Arial headings, Calibri body) | Document title line (full formal title) |
| Section order (1–11) | Status, Date, Author, Org, Version |
| H1: navy 15pt bold + blue bottom border | All section content |
| H2: blue 12pt bold, no border | FR subsection names and count |
| TOC: navy L1 bold / blue L2 indented / grey page numbers | NFR subsection names (if 9.1–9.7 don't all apply) |
| Header: right-aligned blue Arial 9pt + bottom rule | Target Users table rows |
| Footer: centered grey page number + top rule | Bookmark IDs (must match section names) |
| Three sections (cover / meta+TOC / content) | Output filename |
| Page numbers restart at 1 in content section | |
| No header/footer on cover or meta/TOC pages | |