---
name: technical-document
description: "Use this skill whenever the user asks to create a technical document, product document, implementation guide, developer handbook, or deep-dive technical write-up for any project. A technical document answers HOW the system works at implementation level — pipelines, modules, algorithms, agents, formulas, deployment commands, bug fixes, and cost breakdowns. It is distinct from a requirements document (WHAT the system must do) and an architecture document (HOW it is structured at a high level). Triggers: 'create a technical document', 'write a product document', 'document how the system works', 'create an implementation guide', 'write a technical deep-dive for [project]'. Produces a fully formatted .docx + PDF matching MHK Tech Inc. house style."
---

# Technical Document — MHK Tech House Style

A technical document is the **developer's complete reference** for a project. It explains every pipeline step by step, every module file by file, every algorithm formula by formula, every agent turn by turn, every deployment command by command, and every known bug and fix. A reader should be able to understand, run, maintain, and extend the system from this document alone.

**This document is NOT:**
- A requirements doc → that lists FR-NN / NFR-NN items (what the system must do)
- An architecture doc → that describes subsystems and trade-offs at a high level (how it is structured)

**This document IS:**
- A complete implementation reference → every module, every formula, every command, every cost

---

## Step 0 — Critical rules before writing any code

- `docx` is **preinstalled**. `require('docx')` directly. Never run `npm install`.
- Never use `\n` inside a `TextRun` — use separate `Paragraph` elements.
- Never insert `•` literally — use `bullet: { level: 0 }` on a `Paragraph`.
- Table shading: always `ShadingType.CLEAR`, never `SOLID`.
- Tables need `columnWidths` on `Table` AND `width` on every `TableCell`, both `WidthType.PERCENTAGE`. Widths must sum to 100.
- Bookmarks: `new Bookmark({ id, name, children: [...runs] })` — never `BookmarkStart`/`BookmarkEnd` directly.
- `PageReference(bmId)` — `bmId` must exactly match `id` and `name` in `Bookmark`.
- Page size: US Letter `{ width: 12240, height: 15840 }` (DXA — 1440 = 1 inch).
- Code/commands: Courier New, size 18, background `F5F5F5`. Split on `\n` into one Paragraph per line.
- Formulas: Courier New inline runs for math expressions. One formula per line. Bold the result variable.
- Technical docs are long (20–50+ pages). Build content arrays in logical chunks; never put everything in one array.
- Verify output: convert to PDF and read every page before presenting.

---

## Step 1 — Gather content from the user

| Item | Default / Source |
|---|---|
| Project / system name | User prompt or uploaded doc |
| Document type label | "Product Document (PD)" |
| Status | "Active — Production" or "In Development" |
| Date | Current month + year |
| Author | Jyothirmai Chandolu (MHK default) |
| Organization | MHK Tech Inc. |
| Version | "1.0" |
| All module/pipeline/agent content | Derive from project description or uploaded docs |

Ask for clarification on anything ambiguous before writing code. Technical documents require precise content — do not guess at module names, formula values, or command syntax.

---

## Step 2 — Fixed document structure (never change the order)

Every technical document has these sections. The numbered feature sections (5 onwards) vary per project — add one section per major pipeline, module, agent, or feature area. Sections 1–4 and the final three sections are always present.

```
1.  Executive Summary
    — What the system does, what it produces, one-line tech stack, current state

2.  The Problem This Project Solves
    2.1  Why Existing Approaches Fall Short   ← bold-prefix bullets per gap
    2.2  What This Project Provides           ← what it delivers that nothing else does

3.  How It Works — [System Name] Strategy
    3.1  [Primary data/processing tier]
    3.2  [Secondary data/processing tier]
    3.3  [Tertiary/fallback tier]
    3a.  Architecture Diagram                  ← ASCII diagram, always present

4.  The Role of AI / Core Engine in This Project
    4.1  [Model/engine allocation — which tool does what]
    4.2  [What each model/engine is instructed to do]
    4.3  [Anti-hallucination / validation / quality gates]

5–N. [One section per major pipeline, module, agent, or feature]
    Each section follows the Module Deep-Dive pattern (see Step 7)

N+1. Key Design Decisions
    — Batch processing and resumability
    — Rate limiting and API courtesy
    — Two-model / cost strategy
    — Deterministic output
    — [Any project-specific decision]

N+2. Technical Overview
    N+2.1  Technology Stack                    ← always a table
    N+2.2  Running the Project                 ← exact commands
    N+2.3  Output Location / File Structure

N+3. Limitations and Known Gaps

N+4. Summary / Conclusion

N+5. [Infrastructure / Cloud / Cost section — if AWS deployed]
    — One subsection per always-on service
    — One subsection per scheduled job
    — Total monthly cost

```

**Typical section titles from real MHK projects** (adapt as needed):
- Data Pipeline — [Source] Fetching, Validation & KPI Calculation
- AI Chatbot — RAG-Powered Question & Answer System
- How the [Analysis] Works — Scoring, Ranking & Outlier Detection
- Events Pipeline — Automated Event Extraction from SEC Filings
- [Agent Name] Agent — [What It Enriches]
- [Feature Name] Feature
- Daily Automated Data Refresh — Cloud Deployment
- Monthly [Scanner/Updater] — Incremental Update
- Database Migration — [From] to [To]
- AWS Infrastructure — Full Cost Breakdown

---

## Step 3 — Colour palette and typography (exact values — never change)

```js
const C_NAVY  = '1F3864';   // H1 text, cover title, key term labels, formula variable names
const C_BLUE  = '2E5496';   // H2 text, borders/rules, TOC L2, header text, metadata labels
const C_GRAY  = '595959';   // TOC page numbers, footer number, cover sub-labels
const C_WHITE = 'FFFFFF';   // table header text, cell fill (alternating)
const C_SHADE = 'E8EAF6';   // alternating table row shading
const C_BODY  = '2B2B2B';   // all body paragraph text
const C_DKGRAY= '333333';   // table body cell text
const C_CODE  = 'F5F5F5';   // code block / command / formula background
const C_WARN  = 'FFF3CD';   // callout / warning box background (optional)

const FONT  = 'Arial';      // headings, cover, metadata labels, TOC, header, footer
const FBODY = 'Calibri';    // body paragraphs, bullets, table body
const FCODE = 'Courier New';// code blocks, commands, formulas, module names inline

const LINE_SPACING = { line: 259, lineRule: LineRuleType.AUTO };
```

---

## Step 4 — All paragraph helpers (copy verbatim into every build script)

```js
// ── H1: dark navy 15pt Arial bold + blue bottom border ───────────────
const h1 = (text, bmId) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [
    new Bookmark({ id: bmId, name: bmId,
      children: [new TextRun({ text, font: FONT, size: 30, bold: true, color: C_NAVY })] }),
  ],
  border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C_BLUE, space: 6 } },
  spacing: { before: 400, after: 160 },
});

// ── H2: blue 12pt Arial bold, no border ──────────────────────────────
const h2 = (text, bmId) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [
    new Bookmark({ id: bmId, name: bmId,
      children: [new TextRun({ text, font: FONT, size: 24, bold: true, color: C_BLUE })] }),
  ],
  spacing: { before: 280, after: 100 },
});

// ── H3: blue 11pt Arial bold, used for sub-subsections ───────────────
const h3 = (text, bmId) => {
  const children = bmId
    ? [new Bookmark({ id: bmId, name: bmId,
        children: [new TextRun({ text, font: FONT, size: 22, bold: true, color: C_BLUE })] })]
    : [new TextRun({ text, font: FONT, size: 22, bold: true, color: C_BLUE })];
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children,
    spacing: { before: 200, after: 80 },
  });
};

// ── Body paragraph ────────────────────────────────────────────────────
const body = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, font: FBODY, size: 22, color: C_BODY })],
  spacing: { before: opts.before ?? 0, after: opts.after ?? 160, ...LINE_SPACING },
});

// ── Body with mixed bold/plain runs ──────────────────────────────────
// Pass an array of { text, bold?, color? } objects
const bodyMixed = (parts) => new Paragraph({
  children: parts.map(p => new TextRun({
    text: p.text,
    font: FBODY, size: 22,
    bold: p.bold || false,
    color: p.color || C_BODY,
  })),
  spacing: { before: 0, after: 160, ...LINE_SPACING },
});

// ── Bullet: string or TextRun array ──────────────────────────────────
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

// ── Bold-prefix bullet (most common pattern in tech docs) ─────────────
// boldPart: the term/label  restPart: the explanation
const bBullet = (boldPart, restPart) => bullet([
  new TextRun({ text: boldPart, font: FBODY, size: 22, bold: true, color: C_BODY }),
  new TextRun({ text: restPart, font: FBODY, size: 22, color: C_BODY }),
]);

// ── Numbered step (for pipeline step-by-step sections) ───────────────
// stepNum: "Step 1", "Step 2", etc.
const step = (stepNum, title, detail) => [
  new Paragraph({
    children: [
      new TextRun({ text: stepNum + ': ', font: FBODY, size: 22, bold: true, color: C_NAVY }),
      new TextRun({ text: title,          font: FBODY, size: 22, bold: true, color: C_BODY }),
    ],
    spacing: { before: 120, after: 40, ...LINE_SPACING },
  }),
  new Paragraph({
    children: [new TextRun({ text: detail, font: FBODY, size: 22, color: C_BODY })],
    spacing: { before: 0, after: 120, ...LINE_SPACING },
    indent: { left: 360 },
  }),
];
// Usage: ...step('Step 1', 'Fetch SEC Filings', 'Downloads every 8-K...'),

// ── Code block / command block / ASCII diagram ────────────────────────
// Pass multiline string — one Paragraph per line in Courier New on F5F5F5
const codeBlock = (text) =>
  text.split('\n').map(line => new Paragraph({
    children: [new TextRun({ text: line || ' ', font: FCODE, size: 18, color: C_BODY })],
    shading: { fill: C_CODE, type: ShadingType.CLEAR, color: 'auto' },
    spacing: { before: 0, after: 0 },
    indent: { left: 240 },
  }));
// Usage: ...codeBlock(`python fetch.py --index sp500\npython pipeline.py --all`),

// ── Inline code run (inside body Paragraph children) ─────────────────
const code = (text) => new TextRun({ text, font: FCODE, size: 20, color: C_BODY });

// ── Formula block ─────────────────────────────────────────────────────
// Each formula is one codeBlock line; precede with a h3 or body label
const formula = (text) => new Paragraph({
  children: [new TextRun({ text, font: FCODE, size: 20, bold: false, color: C_NAVY })],
  shading: { fill: C_CODE, type: ShadingType.CLEAR, color: 'auto' },
  spacing: { before: 40, after: 40 },
  indent: { left: 360 },
});

// ── Key-value callout (for "why" explanations, notes, warnings) ───────
const callout = (label, text) => new Paragraph({
  children: [
    new TextRun({ text: label + ': ', font: FBODY, size: 22, bold: true, color: C_NAVY }),
    new TextRun({ text,               font: FBODY, size: 22, color: C_BODY }),
  ],
  shading: { fill: C_WARN, type: ShadingType.CLEAR, color: 'auto' },
  indent: { left: 240, right: 240 },
  spacing: { before: 80, after: 80, ...LINE_SPACING },
});

// ── Spacer ────────────────────────────────────────────────────────────
const sp = (before = 0, after = 160) =>
  new Paragraph({ children: [], spacing: { before, after } });

// ── TOC entry ─────────────────────────────────────────────────────────
const tocEntry = (label, bmId, level) => {
  const sz   = level === 1 ? 22 : level === 2 ? 20 : 18;
  const col  = level === 1 ? C_NAVY : C_BLUE;
  const bold = level === 1;
  const left = level === 1 ? 0 : level === 2 ? convertInchesToTwip(0.35) : convertInchesToTwip(0.65);
  return new Paragraph({
    tabStops: [{ type: TabStopType.RIGHT, position: 8640, leader: 'dot' }],
    indent:   { left, hanging: 0 },
    spacing:  { before: 24, after: 24 },
    children: [
      new TextRun({ text: label, font: FONT, size: sz, bold, color: col }),
      new TextRun({ text: '\t',  font: FONT, size: sz }),
      new PageReference(bmId, { font: FONT, size: sz, color: C_GRAY }),
    ],
  });
};
// TOC supports 3 levels: L1=section, L2=subsection, L3=sub-subsection
```

---

## Step 5 — Table helpers

```js
const mkCell = (text, opts = {}) => new TableCell({
  children: [new Paragraph({
    children: [new TextRun({ text, font: FBODY, size: opts.sz || 20,
      bold: opts.bold || false, color: opts.color || C_DKGRAY })],
    spacing: { before: 80, after: 80 },
    indent: { left: 80 },
  })],
  shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR, color: 'auto' } : undefined,
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

// widths must sum to 100
const tableN = (headers, rows, widths) => new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  rows: [
    new TableRow({ children: headers.map((h, i) => hdrCell(h, widths[i])), tableHeader: true }),
    ...rows.map((r, ri) => new TableRow({
      children: r.map((v, ci) => mkCell(v, {
        fill: ri % 2 === 0 ? C_SHADE : C_WHITE,
        w: widths[ci],
      })),
    })),
  ],
  columnWidths: widths.map(w => Math.round(w * 9360 / 100)),
});

// ── Common presets for technical docs ─────────────────────────────────
// Tech stack:        tableN(h, rows, [20, 25, 35, 20])  Layer/Component/Tech/Notes
// Module overview:   tableN(h, rows, [20, 80])           Module/Responsibility
// API endpoints:     tableN(h, rows, [35, 15, 50])       Endpoint/Method/Description
// Bug table:         tableN(h, rows, [25, 40, 35])       Bug/Root Cause/Fix
// Cost breakdown:    tableN(h, rows, [35, 35, 30])       Component/Spec/Monthly Cost
// Schema:            tableN(h, rows, [20, 45, 35])       Table/Key Columns/Purpose
// ADR:               tableN(h, rows, [35, 65])           Decision/Trade-off
```

---

## Step 6 — Document layout (three Word sections)

| Section | Pages | Header | Footer | Page numbers |
|---|---|---|---|---|
| 1 — Cover | 1 | None | None | None |
| 2 — Metadata + TOC | 1–4 | None | None | None |
| 3 — Content | 20–50+ | Right-aligned blue Arial 9pt | Centred grey number | Starts at 1 |

### Cover page

```js
const coverChildren = [
  sp(1800, 0),
  // Project / system title  (large, bold, navy)
  new Paragraph({
    children: [new TextRun({ text: PROJECT_NAME, font: FONT, size: 56, bold: true, color: C_NAVY })],
    spacing: { before: 0, after: 60 },
  }),
  // Descriptive subtitle  (italic blue, smaller)
  new Paragraph({
    children: [new TextRun({ text: DOC_SUBTITLE, font: FONT, size: 28, italics: true, color: C_BLUE })],
    spacing: { before: 0, after: 200 },
  }),
  // Blue decorative rule
  new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 16, color: C_BLUE, space: 8 } },
    spacing: { before: 80, after: 200 },
    children: [],
  }),
  // Document type label
  new Paragraph({
    children: [new TextRun({ text: 'PRODUCT DOCUMENT', font: FONT, size: 22, bold: true, color: C_BLUE })],
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

### Metadata block (second page, before TOC)

```js
// Technical docs use bold-label inline rows (not a table) for metadata
const META_FIELDS = [
  ['Document Type', DOC_TYPE],
  ['Status',        STATUS],
  ['Organization',  ORGANIZATION],
  ['Author',        AUTHOR],
  ['Date',          DATE],
  ['Version',       VERSION],
];

const metaChildren = [
  ...META_FIELDS.map(([label, value], i) => new Paragraph({
    children: [
      new TextRun({ text: label + ':  ', font: FBODY, size: 20, bold: true,  color: C_BLUE }),
      new TextRun({ text: value,          font: FBODY, size: 20, bold: false, color: C_NAVY }),
    ],
    shading: { fill: i % 2 === 0 ? C_SHADE : C_WHITE, type: ShadingType.CLEAR, color: 'auto' },
    indent: { left: 240, right: 240 },
    spacing: { before: 100, after: 100 },
  })),
  sp(240, 0),
];
```

### TOC heading

```js
new Paragraph({
  children: [new TextRun({ text: 'Table of Contents', font: FONT, size: 30, bold: true, color: C_NAVY })],
  border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C_BLUE, space: 6 } },
  spacing: { before: 0, after: 160 },
})
// Then tocEntry() calls for all sections, subsections, and key sub-subsections
// Then sp(120, 0)
```

### Header and footer

```js
const docHeader = new Header({
  children: [new Paragraph({
    children: [new TextRun({ text: `${PROJECT_NAME} — Technical Document`, font: FONT, size: 18, color: C_BLUE })],
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
    // ── Cover (no header/footer) ──────────────────────────────────
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1728, bottom: 1440, left: 1728 } },
        type: SectionType.NEXT_PAGE,
      },
      children: coverChildren,
    },
    // ── Metadata + TOC (no header/footer) ─────────────────────────
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1728, bottom: 1440, left: 1728 } },
        type: SectionType.NEXT_PAGE,
      },
      children: [...metaChildren, ...tocChildren],
    },
    // ── Content (header + footer, page restart at 1) ───────────────
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
  require('fs').writeFileSync('/home/claude/OUTPUT_technical.docx', buf);
  console.log('Written:', buf.length, 'bytes');
});
```

---

## Step 7 — Section writing rules

### Section 1 — Executive Summary
Three to five `body()` paragraphs covering: what the system is, what business question it answers, what it produces (the output artifact), what technology it runs on today, and one sentence on what makes it distinctive. Use `bodyMixed()` to bold the product name and key outputs on first mention.

### Section 2 — The Problem This Project Solves
Opening `body()` sets context. Then `h2('2.1 Why Existing Approaches Fall Short', ...)` — use `bBullet()` for each gap, bold prefix = the gap category, rest = specific failure. Then `h2('2.2 What This Project Provides', ...)` — bullet list of concrete deliverables, one per bullet.

### Section 3 — How It Works — [System] Strategy
Opening `body()` introduces the strategy (e.g. three-tier data collection). One `h2()` per tier/phase, each with `body()` paragraphs explaining: what source/mechanism is used, what it covers, what its limitation is, and how it hands off to the next tier. Then `h2('3a. Architecture Diagram', ...)` with an ASCII flow diagram using `codeBlock()`.

### Section 4 — The Role of AI / Core Engine
`h2('4.1 Model/Engine Allocation', ...)` — always a table: which model/tool does which task, at what cost tier. `h2('4.2 What [Primary Model] Is Asked To Do', ...)` — step-by-step `body()` or `step()` calls describing the exact prompt contract (input format, output format, validation). `h2('4.3 Anti-Hallucination / Quality Gates', ...)` — explain every validation applied to AI/engine output before it is trusted.

### Sections 5–N — Module / Pipeline / Agent / Feature deep-dives

Each feature section follows this **Module Deep-Dive pattern**:

```
h1('NN. [Feature Name] — [What It Does]', 'SNN')

[Opening body paragraph — one sentence summary]

h2('NN.1 [Overview / Architecture Overview]', 'SNNa')
  body() — overall approach, inputs, outputs, key design choice

h2('NN.2 [Primary mechanism / Step-by-step]', 'SNNb')
  step() or bullet() — numbered steps or component breakdown

h2('NN.3 [Data schema / Output format]', 'SNNc')
  tableN() OR codeBlock() — schema table or JSON/CSV structure

h2('NN.4 [Configuration / Commands]', 'SNNd')
  codeBlock() — exact shell commands to run it
  body() — what each flag/option does

h2('NN.5 [Known issues / Bugs fixed / Limitations]', 'SNNe')   ← if applicable
  tableN(['Bug/Issue', 'Root Cause', 'Fix'], rows, [25, 40, 35])
  OR bullet list of limitations
```

**Pipeline sections** (fetch/validate/process loops) use `step()` helpers and `codeBlock()` for the data flow. Always include: what triggers it, what it reads, what it writes, where errors go.

**Agent sections** (ReAct loops, AI agents) use: tool-definition table, turn-by-turn `step()` blocks, max-turns callout, caching strategy, and API endpoint that exposes it.

**Scoring/algorithm sections** use `formula()` for every mathematical expression — one formula per line, variable names bold navy. Follow every formula with a `body()` that defines each variable in plain English.

**Deployment sections** must include: the exact `docker buildx` command, the exact `aws ecs` or deploy commands, EventBridge cron expression, environment variables table, and S3 archive structure using `codeBlock()`.

**Cost sections** follow this pattern per service:
```
h2('NN.N  [Service Name]  (~$XX / month)', 'SNNx')
  tableN(['Component', 'Specification', 'Cost'], rows, [35, 35, 30])
  body() — calculation: "N hours × $X/hour = $Y/month"
```
Always end with a total cost summary table.

### Key Design Decisions section
One `h2()` per decision. Each has: opening `body()` stating the decision, then a `bBullet()` or `callout()` with the rationale. Typical decisions in MHK projects:
- **Batch processing with resumability** — progress file, crash recovery, incremental writes
- **Rate limiting and API courtesy** — exact sleep values per API, User-Agent policy
- **Two-model cost strategy** — which model for which task, cost multiplier
- **Deterministic AI output** — `temperature=0.0`, why this matters for data pipelines
- **[Project-specific]** — any non-obvious choice the next developer would question

### Technical Overview section
`h2('Technology Stack', ...)` — always `tableN(['Layer', 'Component', 'Technology / Library', 'Version / Notes'], rows, [18, 22, 30, 30])`. Every dependency in the codebase gets a row.

`h2('Running the Project', ...)` — exact commands in `codeBlock()`. Group: setup commands, historical run, daily/scheduled run, specific-ticker run, testing.

`h2('Output Location / File Structure', ...)` — `codeBlock()` showing the exact directory tree of outputs, with a comment on what each file/folder contains.

### Limitations and Known Gaps section
Flat `bullet()` list. Each item names a specific limitation, its cause, and (if known) what would fix it. Be honest — this section is for the next developer, not for marketing.

### Summary section
Three to five `body()` paragraphs. Restate what was built, what it produces, what it costs, and what the logical next steps are. Do not introduce new information.

---

## Step 8 — Bookmark ID conventions

```
S1    S2    S21   S22   S3    S31   S32   S33   S3a   S4    S41   S42   S43
S5 … SN    (main feature sections — number matches document section number)
SNNa  SNNb  SNNc  SNNd  SNNe  (subsections of section NN)

SKD   SKD1  SKD2  SKD3  SKD4  SKD5  (Key Design Decisions)
STO   STO1  STO2  STO3          (Technical Overview)
SLim  SSumm                     (Limitations, Summary)
SInfra SInfra1 … SInfraN       (Infrastructure/Cost section)
```

Rule: `id`, `name`, and the matching `tocEntry()` bmId must all be the same string. Keep IDs short, alphanumeric, no spaces.

---

## Step 9 — Required imports

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
node /home/claude/build_PROJECT_technical.js

python /mnt/skills/public/docx/scripts/office/soffice.py \
  --headless --convert-to pdf /home/claude/PROJECT_technical.docx --outdir /home/claude/

pdfinfo /home/claude/PROJECT_technical.pdf | grep Pages
pdftoppm -jpeg -r 130 /home/claude/PROJECT_technical.pdf /home/claude/pg
# View every page: pg-01.jpg through pg-NN.jpg
```

**Visual checklist — every page:**
- Page 1: Cover — large navy title, italic blue subtitle, blue decorative rule, "PRODUCT DOCUMENT" bold blue, grey date·version. No header or footer.
- Page 2+: Metadata rows alternating shading, then "Table of Contents" heading with blue bottom border, then TOC entries (navy bold L1, blue indented L2, grey page numbers). No header or footer.
- Content pages: Right-aligned blue header with bottom rule. Centred grey page number with top rule. H1 dark navy bold 15pt with blue bottom border. H2 blue bold 12pt. H3 blue bold 11pt. Code blocks Courier New on F5F5F5. Formulas indented on F5F5F5. Tables: navy header row, alternating E8EAF6/white body rows. Bold-prefix bullets for principles and decisions.

Copy both `.docx` and `.pdf` to `/mnt/user-data/outputs/` and call `present_files`.

---

## Step 11 — Three-skill comparison at a glance

| Aspect | Technical Document | Architecture Document | Requirements Document |
|---|---|---|---|
| **Core question** | *How does it work at code level?* | *How is it structured at system level?* | *What must it do?* |
| **Primary reader** | Developer / implementer | Architect / senior engineer | Product / stakeholder |
| **Length** | 20–50+ pages | 10–20 pages | 10–15 pages |
| **Document type label** | PRODUCT DOCUMENT | System Design and Architecture Document | PRODUCT REQUIREMENTS DOCUMENT |
| **Cover subtitle** | Italic blue descriptive subtitle | Italic blue doc-type label | "PRODUCT REQUIREMENTS DOCUMENT" bold blue caps |
| **Metadata style** | Inline bold-label rows | Two-column Field/Value table | Alternating-row paragraph pairs |
| **Numbered sections** | 1–4 fixed + N feature sections + fixed closing | 1–15 fixed | 1–11 fixed |
| **Feature sections** | One per pipeline/module/agent/feature | One per component (subsection of Section 4) | One per feature area (subsection of Section 8) |
| **Numbered items** | None — prose + bullets + steps | None — prose + bullets + ADRs | FR-NN / NFR-NN requirement lines |
| **Formulas** | Yes — `formula()` in Courier New on F5F5F5 | No | No |
| **Step-by-step** | Yes — `step()` helper per pipeline step | No | No |
| **Code/commands** | Yes — `codeBlock()` extensively | Yes — diagrams only | No |
| **Bug/fix tables** | Yes | No | No |
| **Cost breakdown** | Yes — per service with formula | Yes — summary table only | No |
| **ADR blocks** | No — use Key Design Decisions section | Yes — Section 14 | No |
| **TOC depth** | 3 levels (H1 / H2 / H3 where key) | 2 levels (H1 / H2) | 2 levels (H1 / H2) |
| **Target Users table** | No | No | Yes — Section 7 |
| **Tech Stack table** | Yes — Technical Overview section | Yes — Section 13 | No |
| **Assumptions** | No | No | Yes — Section 10 |
| **Constraints** | No — use Limitations section | No | Yes — Section 11 |
| **Future section** | Mentioned in Summary | Yes — Section 15 full section | No |