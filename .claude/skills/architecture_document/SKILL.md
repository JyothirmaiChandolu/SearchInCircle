---
name: architecture-document
description: "Use this skill whenever the user asks to create a system design document, architecture document, technical design doc, or any document that describes how a system is built — not what it must do. Triggers include: 'create an architecture doc', 'write a system design document', 'make a technical document for [project name]', 'document the architecture of [system]', or any request to produce a formal Word document describing system components, data flows, infrastructure, deployment, security, or technical decisions. This skill produces a fully formatted .docx (plus PDF preview) that exactly matches the MHK Tech Inc. house style used across the CEO Transition Impact Analysis and SOS Entity Status Monitoring Dashboard architecture documents."
---

# Architecture / System Design Document — MHK Tech House Style

Produces a polished `.docx` + `.pdf` from any project's technical description. The output always has the same structure, colours, fonts, and section order — only the content changes per project.

---

## Step 0 — Read this before writing a single line

- `docx` is **preinstalled**. `require('docx')` directly. Do NOT run `npm install`.
- Never use `\n` inside a `TextRun` — use separate `Paragraph` elements.
- Never insert `•` literally — use `bullet: { level: 0 }` on a `Paragraph`.
- `PageBreak` must be inside a `Paragraph`.
- Table shading: always `ShadingType.CLEAR`, never `SOLID`.
- Tables need `columnWidths` on the `Table` AND `width` on every `TableCell`, both in `WidthType.PERCENTAGE`. Column widths must sum to 100.
- Bookmarks: use `new Bookmark({ id, name, children: [...runs] })` — **never** `BookmarkStart`/`BookmarkEnd` directly.
- `PageReference(bmId)` emits a live PAGEREF field. The `bmId` string must exactly match the `id` and `name` passed to `Bookmark`.
- Page size is **US Letter**: `{ width: 12240, height: 15840 }` (DXA; 1440 = 1 inch).
- Code blocks and diagrams: use a `Paragraph` with `style: 'Code'` or a monospace `TextRun` with `font: 'Courier New'`, `size: 18`, shaded background `fill: 'F5F5F5'`.
- Verify output: convert to PDF and read every page before presenting.

---

## Step 1 — Gather content from the user

Before writing any code, extract or ask for:

| Item | Source |
|---|---|
| Project / system name | User prompt or uploaded doc |
| Document type label | "System Design and Architecture Document" (default) |
| Status | e.g. "Approved — reflects the deployed production system" |
| Date / Last Updated | Current date |
| Author | Ask if unknown (default: Jyothirmai Chandolu) |
| Organization | MHK Tech Inc. (default) |
| Version | "1.0" unless stated otherwise |
| Employee ID | 800342 (default for Jyothirmai) |
| Related Documents | e.g. "Business Requirements Document; Project Documentation" |
| All section content | Derive from project description; ask if ambiguous |

---

## Step 2 — Fixed document structure (never change the order)

Every architecture document has exactly these 15 numbered sections. Add subsections as needed per project; never remove a section — write "Not applicable for this project." if genuinely empty.

```
1.  System Overview
2.  Architecture Principles
3.  High-Level Architecture          ← always includes an ASCII/text diagram
4.  Component Architecture
    4.1 … 4.N  (one per major component)
5.  Data Architecture
    5.1 Database Schema
    5.2 Canonical Data Model / Status Model
    5.3 End-to-End Data Flow         ← always includes a flow diagram
6.  API Architecture
    6.1 Endpoint Surface             ← always a table
    6.2 Authentication
7.  Scheduling Architecture
8.  Deployment Architecture (AWS)
    8.1 Architecture Diagram         ← ASCII diagram
    8.2 Component Reference          ← always a table
    8.3 Network and Routing
    8.4 CI/CD
9.  Security Architecture
10. Resilience and Fault Tolerance
11. Scalability Considerations
12. Logging and Observability
13. Technology Stack                 ← always a table
14. Architectural Trade-offs         ← always a table OR ADR blocks
15. Future Architecture Enhancements
```

---

## Step 3 — Colour palette and typography (exact values — do not change)

```js
const C_NAVY  = '1F3864';   // H1 text, cover title, metadata values, ADR labels
const C_BLUE  = '2E5496';   // H2 text, borders/rules, TOC L2, header text, metadata labels
const C_GRAY  = '595959';   // TOC page numbers, footer number, cover sub-labels
const C_WHITE = 'FFFFFF';   // table header text, cell fill
const C_SHADE = 'E8EAF6';   // alternating metadata + table row shading
const C_BODY  = '2B2B2B';   // all body paragraph text
const C_DKGRAY= '333333';   // table body cell text
const C_CODE  = 'F5F5F5';   // code block / diagram background shading

const FONT  = 'Arial';      // headings, cover, metadata labels, TOC, header, footer
const FBODY = 'Calibri';    // body paragraphs, bullets, table body
const FCODE = 'Courier New';// code blocks, ASCII diagrams, inline code

const LINE_SPACING = { line: 259, lineRule: LineRuleType.AUTO };
```

---

## Step 4 — Paragraph helpers (copy verbatim into every build script)

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

// ── Body paragraph ────────────────────────────────────────────────────
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

// ── Code block / ASCII diagram ────────────────────────────────────────
// Pass a single multiline string; split on \n and emit one Paragraph per line
const codeBlock = (text) => {
  const lines = text.split('\n');
  return lines.map(line => new Paragraph({
    children: [new TextRun({ text: line || ' ', font: FCODE, size: 18, color: C_BODY })],
    shading: { fill: C_CODE, type: ShadingType.CLEAR, color: 'auto' },
    spacing: { before: 0, after: 0 },
    indent: { left: 240 },
  }));
};
// Usage: ...codeBlock(`line1\nline2\nline3`),

// ── Inline code run (use inside a body Paragraph's children array) ────
const code = (text) =>
  new TextRun({ text, font: FCODE, size: 20, color: C_BODY });

// ── ADR block (Decision / Rationale / Trade-off) ─────────────────────
// Used in Section 14 when documenting architectural decisions
const adr = (title, bmId, decision, rationale, tradeoff) => [
  h2(title, bmId),
  new Paragraph({
    children: [
      new TextRun({ text: 'Decision. ', font: FBODY, size: 22, bold: true, color: C_NAVY }),
      new TextRun({ text: decision,     font: FBODY, size: 22, color: C_BODY }),
    ],
    spacing: { before: 80, after: 80, ...LINE_SPACING },
  }),
  new Paragraph({
    children: [
      new TextRun({ text: 'Rationale. ', font: FBODY, size: 22, bold: true, color: C_NAVY }),
      new TextRun({ text: rationale,    font: FBODY, size: 22, color: C_BODY }),
    ],
    spacing: { before: 80, after: 80, ...LINE_SPACING },
  }),
  new Paragraph({
    children: [
      new TextRun({ text: 'Trade-off. ', font: FBODY, size: 22, bold: true, color: C_NAVY }),
      new TextRun({ text: tradeoff,     font: FBODY, size: 22, color: C_BODY }),
    ],
    spacing: { before: 80, after: 160, ...LINE_SPACING },
  }),
  new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C_SHADE, space: 4 } },
    spacing: { before: 0, after: 160 },
    children: [],
  }),
];
// Usage: ...adr('ADR-01: Title', 'ADR01', 'We decided...', 'Because...', 'The cost is...'),

// ── Spacer ────────────────────────────────────────────────────────────
const sp = (before = 0, after = 160) =>
  new Paragraph({ children: [], spacing: { before, after } });

// ── TOC entry ─────────────────────────────────────────────────────────
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

## Step 5 — Table helpers (used extensively in architecture docs)

Architecture docs use more tables than requirement docs. There are three table patterns:

```js
// ── Standard 2-column table (API endpoints, component reference, etc.) ─
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

// widths: array of column width percentages — must sum to 100
const tableN = (headers, rows, widths) => new Table({
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

// ── Common table presets ───────────────────────────────────────────────
// 2-column:  tableN(headers, rows, [30, 70])
// 3-column:  tableN(headers, rows, [25, 40, 35])
// 4-column:  tableN(headers, rows, [20, 25, 30, 25])
// 5-column:  tableN(headers, rows, [15, 20, 25, 20, 20])
//
// Section 6.1 API table:     [30, 70]  or  [25, 75]
// Section 8.2 Component ref: [20, 80]
// Section 13 Tech stack:     [20, 20, 35, 25]  (Layer / Component / Technology / Notes)
// Section 14 Trade-offs:     [35, 65]  (Decision / Trade-off accepted)
```

---

## Step 6 — Three-section document layout

| Section | Pages | Header | Footer | Page numbers |
|---|---|---|---|---|
| 1 — Cover | 1 page | None | None | Not shown |
| 2 — Metadata + TOC | 1–3 pages | None | None | Not shown |
| 3 — Content | All remaining | Right-aligned, blue, Arial 9pt | Centered number, Arial 9pt | Starts at 1 |

### Cover page children

```js
const coverChildren = [
  sp(1800, 0),
  // System name (line 1 of title)
  new Paragraph({
    children: [new TextRun({ text: SYSTEM_NAME, font: FONT, size: 56, bold: true, color: C_NAVY })],
    spacing: { before: 0, after: 60 },
  }),
  // Document type (line 2 of title)
  new Paragraph({
    children: [new TextRun({ text: DOC_TYPE_LABEL, font: FONT, size: 28, bold: false, color: C_BLUE, italics: true })],
    spacing: { before: 0, after: 160 },
  }),
  // Org · Project Code
  new Paragraph({
    children: [new TextRun({ text: `${ORGANIZATION}  ·  ${PROJECT_CODE}`, font: FONT, size: 20, color: C_GRAY })],
    spacing: { before: 0, after: 0 },
  }),
  sp(1600, 0),
];
```

> **Note on cover style:** Architecture docs use a slightly different cover from requirements docs. The title is the system name only (not split across two lines). The subtitle is the document type in italics blue. The third line is org · project code in grey. No decorative rule, no "VERSION 1.0" label — those go in the metadata table.

### Metadata page children

```js
// Architecture docs use a two-column table for metadata, not alternating rows
const META_ROWS = [
  ['Document Title',   FULL_DOC_TITLE],
  ['Project Name',     PROJECT_NAME_FULL],
  ['Organization',     ORGANIZATION],
  ['Author',           AUTHOR],
  ['Employee ID',      EMPLOYEE_ID],
  ['Document Version', VERSION],
  ['Status',           STATUS],
  ['Last Updated',     DATE],
  ['Related Documents', RELATED_DOCS],
];

const metaChildren = [
  h1('Document Metadata', 'SMeta'),   // Section 0 — not numbered in TOC
  tableN(
    ['Field', 'Value'],
    META_ROWS,
    [30, 70],
  ),
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

Then one `tocEntry(label, bmId, level)` per section and subsection, followed by `sp(120, 0)`.

### Header and footer (content section only)

```js
const docHeader = new Header({
  children: [new Paragraph({
    children: [new TextRun({
      text: `${SYSTEM_NAME} — ${DOC_TYPE_SHORT}`,  // e.g. "SOS ESD — Architecture Document"
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
    // ── Section 1: Cover ──────────────────────────────────────────
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
    // ── Section 2: Metadata + TOC ─────────────────────────────────
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
  require('fs').writeFileSync('/home/claude/OUTPUT.docx', buf);
  console.log('Written:', buf.length, 'bytes');
});
```

---

## Step 7 — Section-by-section writing rules

### Section 1 — System Overview
Two to four `body()` paragraphs. Must answer: what is the system, what problem does it solve, how does it work in one sentence (the "architecture in one line"), and what is its current deployment state? The one-liner pattern: `body('Architecture in one line:  React + FastAPI (ECS Fargate) + PostgreSQL (RDS), fronted by CloudFront.')` — monospace the tech stack names with `code()` runs.

### Section 2 — Architecture Principles
Opening `body()` paragraph ("N principles govern every design decision."). Then one `bullet()` per principle. Each bullet starts with a bold principle name followed by a plain explanation:
```js
bullet([
  new TextRun({ text: 'Principle name — ', font: FBODY, size: 22, bold: true, color: C_BODY }),
  new TextRun({ text: 'Explanation of what it means and why.',  font: FBODY, size: 22, color: C_BODY }),
])
```
Typical principles across MHK projects: Redundancy over single-source dependence · Fully async I/O · Validate before persist · Append-only history · Normalize at the boundary · Minimum viable infrastructure · Deterministic AI output · Anti-hallucination by construction · Resumable batch processing · Separation of compute from storage.

### Section 3 — High-Level Architecture
Opening `body()` describing the overall topology. Then an ASCII/text architecture diagram using `codeBlock()`. Then a second `body()` explaining what the two independent compute paths are (always-on service + scheduled batch). Keep diagrams simple — boxes with `+---+` borders and `-->` arrows as in the SOS and CEO documents.

### Section 4 — Component Architecture
One `h2()` per major component (frontend, backend API, database, external integrations, pipelines, storage, notifications). Each subsection has one to three `body()` paragraphs. Name the technology first, then explain its role, then call out any non-obvious design choice. Keep each subsection to one paragraph unless genuinely complex.

### Section 5 — Data Architecture

**5.1 Database Schema** — use a `tableN()` to list each table with its key columns and purpose. Pattern: `['Table', 'Key Columns', 'Purpose']` with widths `[20, 45, 35]`.

**5.2 Canonical Data/Status Model** — `body()` describing how raw vocabulary from different sources is normalized to one canonical set. List the canonical values inline in the body text.

**5.3 End-to-End Data Flow** — always a `codeBlock()` ASCII flow diagram showing the ETL/pipeline steps with arrows, followed by a `body()` explaining it.

### Section 6 — API Architecture

**6.1 Endpoint Surface** — always a table with headers `['Endpoint', 'Purpose']` or `['Endpoint group', 'Purpose']`. Widths `[35, 65]`. List every exposed route. Group related routes in the same row if they share a clear purpose.

**6.2 Authentication** — `body()` paragraph. Describe the auth mechanism (API key header, JWT, none) and which endpoints are exempt.

### Section 7 — Scheduling Architecture
One or two `body()` paragraphs. State what triggers the scheduled job (EventBridge cron, in-process scheduler, external), what it runs (ECS RunTask, Celery, etc.), and why the chosen approach is better than alternatives. Include the specific cron expression if known.

### Section 8 — Deployment Architecture (AWS)

**8.1 Architecture Diagram** — `codeBlock()` ASCII diagram showing CloudFront → ECS → RDS/S3 topology, plus the EventBridge → ECS scheduled task path.

**8.2 Component Reference** — table with headers `['Component', 'Role']`, widths `[20, 80]`. One row per AWS service used. Be specific: what exactly does this service do in this project.

**8.3 Network and Routing** — `body()` paragraph. Explain any non-obvious routing (e.g. nip.io DNS trick, CloudFront path-based routing, VPC security groups).

**8.4 CI/CD** — `body()` paragraph. Describe the deployment pipeline: how code gets from git to production for both frontend and backend. Include the `docker buildx build --platform linux/amd64` requirement if Fargate is used.

### Section 9 — Security Architecture
Flat `bullet()` list. Each bullet is one security control: API auth, database isolation, IAM least-privilege, secret handling, log hygiene, no-secrets-in-git. Use the bold-prefix bullet pattern. Be specific — name the actual mechanism, not just the category.

### Section 10 — Resilience and Fault Tolerance
Flat `bullet()` list. Each bullet is one resilience mechanism: source fallback, validation gate, graceful degradation, bounded concurrency, append-only history. Use the bold-prefix bullet pattern.

### Section 11 — Scalability Considerations
Flat `bullet()` list. Cover: stateless backend, async concurrency, compute model (Fargate vs EC2), current bottleneck. Always end with a "Current bottleneck" bullet that names the real limit honestly.

### Section 12 — Logging and Observability
Flat `bullet()` list. Cover: where logs go (CloudWatch), per-run log files, S3 archiving of logs, rejected record handling, any alerting or monitoring in place.

### Section 13 — Technology Stack
Always a table. Headers: `['Layer', 'Component', 'Technology / Library', 'Version / Notes']`. Widths `[18, 22, 30, 30]`. Every dependency gets a row. Group by: Language · Web framework · ORM/DB driver · Validation · HTTP client · Frontend framework · Styling · Database · AI/LLM models · Vector store · Containerization · Compute · Frontend hosting · CDN · Database hosting · Object storage · Scheduling · Container registry · Logging · Infra tooling.

### Section 14 — Architectural Trade-offs
Use the **ADR (Architectural Decision Record) block** pattern for each decision:
```
ADR-NN: Short Decision Title
Decision. One sentence — what was chosen.
Rationale. Why this was the right call.
Trade-off. What was accepted / sacrificed.
--- (thin separator rule) ---
```
Use the `adr()` helper from Step 4. Alternatively, use a two-column table `['Decision', 'Trade-off accepted']` for simpler projects. Typical ADR topics: load balancer vs direct IP, secrets manager vs env vars, IaC vs plain CLI, single image vs multiple images, always-on vs ephemeral compute, multi-tenant vs single-org.

### Section 15 — Future Architecture Enhancements
Flat `bullet()` list of 5–8 improvements not yet implemented. Order roughly by priority. Each bullet names the change and the reason it would help. Use future tense. End with at least one infrastructure-scale or auth-layer improvement.

---

## Step 8 — Bookmark ID conventions

```
SMeta                       ← Document Metadata (not in TOC — used by metadata table)
S1  S2  S3  S4  S5  S6      ← Sections 1–6
S7  S8  S9  S10 S11 S12     ← Sections 7–12
S13 S14 S15                 ← Sections 13–15

S41 S42 S43 … S4N           ← Component Architecture subsections
S51 S52 S53                 ← Data Architecture subsections
S61 S62                     ← API Architecture subsections
S81 S82 S83 S84             ← Deployment Architecture subsections

ADR01 ADR02 … ADRN          ← Architectural Decision Records (Section 14)
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
node /home/claude/build_PROJECT_arch.js

# Convert to PDF
python /mnt/skills/public/docx/scripts/office/soffice.py \
  --headless --convert-to pdf /home/claude/PROJECT_arch.docx --outdir /home/claude/

# Get page count, then render and read every page
pdfinfo /home/claude/PROJECT_arch.pdf | grep Pages
pdftoppm -jpeg -r 130 /home/claude/PROJECT_arch.pdf /home/claude/pg
# Then view /home/claude/pg-01.jpg through pg-NN.jpg
```

**Check every page before presenting:**
- Page 1: Cover — large navy system name, italic blue doc-type subtitle, grey org·code. No header or footer.
- Page 2: Metadata table (navy header row, alternating shading) + "Table of Contents" heading + TOC entries with dot leaders and page numbers. No header or footer.
- Page 3+: Right-aligned blue header with bottom rule. Centred grey page number with top rule. H1 dark navy with bottom border. H2 blue, no border. Bullets indented 0.35″. Code blocks in Courier New on `F5F5F5` background. ADR blocks end with a thin separator rule.

Copy both files to `/mnt/user-data/outputs/` and call `present_files`.

---

## Step 11 — What varies per project vs what never changes

| Always the same | Changes per project |
|---|---|
| All 8 hex colour values | System name |
| Font stack (Arial headings, Calibri body, Courier New code) | Document type label and subtitle |
| 15-section order | Status, Date, Author, Org, Version, Employee ID |
| H1: navy 15pt bold + blue bottom border | All section content |
| H2: blue 12pt bold, no border | Component names and count (Section 4) |
| Cover: system name + italic blue subtitle + grey org·code | Database table names and schema |
| Metadata: two-column table (Field / Value) | API endpoint list |
| TOC: navy L1 bold / blue L2 indented / grey page numbers | AWS service set and costs |
| Header: right-aligned blue Arial 9pt + bottom rule | ADR titles and count |
| Footer: centred grey page number + top rule | Technology stack rows |
| Three Word sections (cover / meta+TOC / content) | Future enhancements list |
| Page numbers restart at 1 in content section | Bookmark IDs (must match section names) |
| No header/footer on cover or meta/TOC pages | Output filename |
| Code blocks: Courier New 9pt on F5F5F5 background | |
| ADR pattern: Decision · Rationale · Trade-off + separator | |

---

## Quick comparison: Architecture doc vs Requirements doc

| Aspect | Architecture Doc | Requirements Doc |
|---|---|---|
| Question answered | *How is it built?* | *What must it do?* |
| Cover subtitle | Italic blue doc-type label | "PRODUCT REQUIREMENTS DOCUMENT" in bold blue caps |
| Metadata block | 2-col table (Field / Value) | Alternating-row paragraph pairs |
| Section count | 15 | 11 |
| Numbered items | None (ADRs use ADR-NN prefix) | FR-NN and NFR-NN prefixed bullets |
| Code/diagrams | Yes — `codeBlock()` in Courier New | No |
| ADR blocks | Yes — Section 14 | No |
| Target Users section | No | Yes — Section 7, always a table |
| Tech Stack section | Yes — Section 13, always a table | No |
| Trade-offs section | Yes — Section 14, ADR blocks or table | No |
| Future Enhancements | Yes — Section 15, bullet list | No |
| Assumptions section | No | Yes — Section 10, bullet list |
| Constraints section | No | Yes — Section 11, 4 subsections |