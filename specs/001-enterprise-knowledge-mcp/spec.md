# Feature Specification: Enterprise Knowledge MCP Server & Preprocessing Skill

**Feature Branch**: `001-enterprise-knowledge-mcp`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "請參照 Task 1 & Task 2 - Enterprise Knowledge MCP Server.pdf 以及憲章"

## Overview

A production-ready enterprise document knowledge base delivered in two forms that share one
processing core:

- **Knowledge base service** — ingests unstructured enterprise documents (DOCX / PDF / PPTX),
  processes them into structure-preserving, metadata-complete passages, indexes them for
  hybrid search, and exposes them to AI agents through a remote knowledge interface so agents
  can answer questions with precise citations (page or slide).
- **Reusable preprocessing capability** — packages the same parse → clean → chunk logic as a
  standalone, single-file tool that any agent can run locally to turn one document into
  index-ready structured output, without starting the service or touching the index.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Query enterprise knowledge with citations (Priority: P1)

An AI agent (e.g. Claude Desktop / Claude Code) connected to the knowledge base asks a natural
language question and receives the most relevant passages from the indexed corpus, each
carrying its source document, page or slide number, and section context, so the agent can
answer accurately and cite the source.

**Why this priority**: This is the headline value — turning a pile of enterprise documents into
answerable, citable knowledge. Without it the system delivers nothing to end users.

**Independent Test**: With a pre-indexed corpus, issue queries such as "What is the yield
improvement plan?", "Show me the KPI table from the Q4 report", and "Summarize slide 5"; verify
returned passages are topically relevant, carry complete citation metadata, and that exact-term
queries (proper nouns, identifiers) and paraphrased/semantic queries both surface the right
passages.

**Acceptance Scenarios**:

1. **Given** an indexed corpus, **When** the agent searches a paraphrased question, **Then** the
   system returns a ranked list of relevant passages each with document name, page/slide number,
   section title, passage type, and a relevance score.
2. **Given** a query containing a rare exact term or identifier, **When** the agent searches,
   **Then** passages containing that exact term are surfaced even if semantically similar
   wording ranks them low.
3. **Given** a query in mixed Chinese/English, **When** the agent searches, **Then** relevant
   passages in either language are retrieved.
4. **Given** a search request, **When** the tool is invoked, **Then** the invocation (tool name,
   query, and identifiers of returned passages) is recorded in a server-side log that an
   operator can inspect.

---

### User Story 2 - Self-service document ingestion (Priority: P2)

An operator adds a new enterprise document to the knowledge base and it becomes searchable
immediately, without restarting or re-deploying the service.

**Why this priority**: Keeps the knowledge base current; a static corpus loses value quickly.
Depends on the ingestion pipeline that also underpins P1.

**Independent Test**: Submit a DOCX, a PDF, and a PPTX; confirm each returns a success result
reporting how many passages were produced, and that a subsequent search finds content from the
just-added document with no restart.

**Acceptance Scenarios**:

1. **Given** the running service, **When** an operator submits a supported document, **Then** the
   system parses, cleans, chunks, and indexes it and reports the resulting passage count.
2. **Given** a freshly submitted document, **When** the agent searches for its content, **Then**
   the new passages appear in results without any restart.
3. **Given** a document is being processed, **When** other requests arrive, **Then** the service
   remains responsive (long processing does not block concurrent requests).
4. **Given** an unsupported file type or an oversized file, **When** it is submitted, **Then** the
   system rejects it with a clear error and does not index it.

---

### User Story 3 - Inspect the catalogue and retrieve specific items (Priority: P3)

An agent or operator lists everything currently indexed, inspects a specific document's summary
(passage count, page/slide range), and fetches the full content and metadata of an individual
passage.

**Why this priority**: Supports navigation, verification, and follow-up drill-down after a
search; valuable but secondary to search itself.

**Independent Test**: Call the catalogue listing and confirm it enumerates all indexed documents;
request one document and confirm its summary; request one passage by its identifier and confirm
full content plus complete metadata are returned.

**Acceptance Scenarios**:

1. **Given** an indexed corpus, **When** the catalogue is listed, **Then** all indexed documents
   are enumerated with identifying metadata.
2. **Given** a document identifier, **When** its document-level record is requested, **Then** the
   system returns a summary including passage count and page/slide range.
3. **Given** a passage identifier, **When** that passage is requested, **Then** the system returns
   its full content and complete metadata.
4. **Given** an unknown document or passage identifier, **When** it is requested, **Then** the
   system returns a clear not-found result rather than failing opaquely.

---

### User Story 4 - Reusable single-file preprocessing (Priority: P4)

A developer or agent runs a standalone tool against one DOCX/PDF/PPTX file to produce
index-ready structured output (machine-readable data plus a human-readable rendering) without
starting the service, touching the index, or connecting to any network.

**Why this priority**: Delivers the processing core as a reusable capability for ad-hoc and CI
use. Independent of the running service, but built on the same core, so it follows P1–P3.

**Independent Test**: Run the tool on a real document with the full pipeline; confirm it emits
structured output whose passages match the schema and count the knowledge base would produce for
the same file; confirm it can run individual stages (parse only, clean only, chunk only) and
that it refuses unsupported types, missing files, and oversized files.

**Acceptance Scenarios**:

1. **Given** a supported document, **When** the tool runs the full pipeline, **Then** it writes
   structured output and a human-readable rendering, and the passages are identical to what the
   knowledge base would index for that file.
2. **Given** the tool runs, **When** an operator selects a single stage or output format, **Then**
   only the requested stage/format is produced.
3. **Given** an unsupported extension, a missing file, or an oversized file, **When** the tool
   runs, **Then** it emits a single-line error and a non-zero exit status without a raw stack
   trace.
4. **Given** the tool runs, **When** it writes output, **Then** all writes stay inside the
   declared output directory, the input file is never modified, and no network calls are made.

---

### Edge Cases

- Documents containing repeated headers/footers, page-number-only lines, and pure-symbol noise —
  these MUST be removed while titles, tables, figures, and page/slide origin are preserved.
- Short titles — MUST NOT be dropped by any minimum-length cleaning rule.
- Tables and figures — each MUST become its own passage; table content MUST be preserved in a
  structured, readable form.
- A section longer than the soft size limit — MUST be split only between whole elements, never
  mid-sentence or mid-row, with continued passages retaining the same section context.
- Page/slide boundary changes within a continuous section — MUST start a new passage.
- Images embedded in slides/documents that carry text — that text MUST be recovered so
  figure-borne content is searchable.
- Mixed Chinese/English content and non-ASCII output — MUST be handled without character
  corruption.
- Empty query, unknown identifier, corrupt/unreadable document — MUST return a clear, structured
  error.

## Requirements *(mandatory)*

### Functional Requirements

**Ingestion & processing**

- **FR-001**: System MUST accept DOCX, PDF, and PPTX documents that may contain multiple pages,
  headers/footers, tables, images, captions, and slide structure.
- **FR-002**: System MUST parse documents in a way that preserves structure and provenance —
  titles, tables, figures, and per-element page numbers (PDF/DOCX) or slide numbers (PPTX) —
  rather than reducing them to flat text.
- **FR-003**: System MUST recover text embedded in images so figure/slide-borne text is not lost.
- **FR-004**: System MUST clean content by removing repeated header/footer boilerplate (appearing
  at or above a repetition threshold), page-number-only lines, and pure-symbol/no-substance
  paragraphs, while preserving document structure, titles, tables, figures, and page/slide
  numbering.
- **FR-005**: System MUST split content along semantic boundaries (section / table / figure /
  page / slide) and MUST NOT split by fixed character or token count. Each table and each figure
  MUST become its own passage. A passage MAY be divided only when a section exceeds a configurable
  soft size limit, and only between whole elements.

**Passage metadata (the contract)**

- **FR-006**: Every passage MUST carry the complete metadata schema: document identifier, original
  filename, page number (or null), slide number (or null), a unique and reproducible passage
  identifier of the form `<document_id>-<sequence>`, passage type (text / table / figure), the
  passage content (tables rendered in structured readable form), and section title (or null).

**Retrieval**

- **FR-007**: System MUST retrieve passages using a hybrid of semantic (meaning-based) and lexical
  (exact-term) matching combined by a rank-based fusion, and MUST NOT rely on a single retrieval
  method or plain full-text search as the final retrieval strategy.
- **FR-008**: Retrieval MUST surface both semantically similar/paraphrased matches and exact rare
  terms/identifiers, and MUST work for mixed Chinese/English content.
- **FR-009**: Search results MUST include, for each passage, its content, complete metadata, and a
  relevance score, ordered by relevance.

**Agent-facing interface**

- **FR-010**: System MUST expose the knowledge base to remote AI agents as a knowledge interface
  providing these capabilities: (a) search for the most relevant passages given a query and a
  result count; (b) list the catalogue of indexed documents; (c) retrieve a document-level record
  (passage count, page/slide range) by document identifier; (d) retrieve a single passage's full
  content and metadata by passage identifier. It MUST also expose browsable resources for the full
  catalogue and for an individual document with all its passages.
- **FR-011**: System MUST record each knowledge-interface invocation in an inspectable server-side
  log capturing at least the operation name, the query, and identifiers of the returned passages.

**Live ingestion**

- **FR-012**: Operators MUST be able to add a document to a running service and have it become
  searchable immediately, with no restart or redeploy; the submission MUST report the number of
  passages produced.
- **FR-013**: System MUST reject unsupported file types and files above a configured size limit
  with a clear error, without indexing them.
- **FR-014**: Long-running processing MUST NOT block the service from handling concurrent requests.

**Reusable preprocessing capability**

- **FR-015**: System MUST provide a standalone, single-file preprocessing tool that produces
  index-ready structured output and a human-readable rendering from one DOCX/PDF/PPTX file, reusing
  the exact same parse/clean/chunk core so its passages are identical to what the knowledge base
  indexes for the same file.
- **FR-016**: The preprocessing tool MUST allow selecting which pipeline stage(s) to run and which
  output format(s) to emit, and MUST allow overriding the document-identifier prefix, size limit,
  soft split limit, and image-text recovery on/off.
- **FR-017**: The preprocessing tool MUST enforce safety boundaries: input opened read-only and
  never modified; only supported extensions accepted; oversized inputs rejected; all writes
  confined to the declared output directory with path-escape refused; no database writes; no
  outbound network calls. On error it MUST emit a single-line error with a non-zero exit status and
  no raw stack trace.

**Reuse discipline**

- **FR-018**: Parse, clean, and chunk logic MUST exist in a single shared implementation reused by
  both the service and the preprocessing tool; the tool MUST NOT reimplement or copy that logic.

**Deployment, persistence & operability**

- **FR-019**: System MUST be deployable to a reachable public secure (HTTPS) URL and MUST offer a
  health check and a landing page that dynamically lists the currently available knowledge-interface
  capabilities and resources.
- **FR-020**: Indexed data, uploaded files, and downloaded model assets MUST persist across restart
  and redeploy.
- **FR-021**: System MUST run on the target deployment hardware — a 64-bit ARM compute node with no
  GPU — meaning all processing runs CPU-only and all components are compatible with that
  architecture. (See constitution: ARM64 CPU-only runtime constraint.)

**Verification evidence**

- **FR-022**: System MUST provide a client verification demonstration that exercises a running
  service through the real agent protocol and produces inspectable server logs of the tool calls.

### Key Entities

- **Document**: A source enterprise file (DOCX/PDF/PPTX). Attributes: document identifier, original
  filename, format, page/slide range, passage count.
- **Passage (Chunk)**: The atomic unit of retrieval produced by semantic-boundary chunking.
  Attributes as in FR-006: document identifier, filename, page number, slide number, unique
  reproducible passage identifier, passage type (text/table/figure), content, section title.
- **Search Result**: A passage returned for a query, augmented with a relevance score and ordering.
- **Catalogue**: The set of all indexed documents and their summaries.
- **Preprocessing Output**: For a single document, the structured (machine-readable) and
  human-readable renderings of the parse/clean/chunk stages, whose passages match the indexed
  passages for that document.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For all three supported formats (DOCX, PDF, PPTX), 100% of produced passages carry
  every required metadata field populated correctly (correct page/slide origin, unique reproducible
  identifier, correct passage type).
- **SC-002**: Zero passages are produced by fixed-size splitting; every split occurs on a semantic
  boundary between whole elements (verifiable: no passage cuts a sentence or a table row).
- **SC-003**: For a benchmark question set covering paraphrased queries, exact-term/identifier
  queries, and mixed Chinese/English queries, the correct passage appears in the top results for at
  least 90% of questions.
- **SC-004**: A newly added document is searchable within the same running session with no restart,
  and its returned passage count equals the count reported at ingestion.
- **SC-005**: The standalone preprocessing tool produces, for a given document, a passage set
  identical (same count and metadata) to what the knowledge base indexes for that document.
- **SC-006**: The service is reachable at a public HTTPS URL with a working health check, and
  indexed data survives a restart/redeploy (a document indexed before restart is still searchable
  after).
- **SC-007**: An operator can, from server logs alone, confirm for any search which query ran and
  which passages were returned.
- **SC-008**: The preprocessing tool rejects every unsupported extension, missing file, and
  oversized file with a single-line error and a non-zero exit status, and never modifies its input
  or writes outside the declared output directory.

## Assumptions

- The corpus is enterprise business documents (reports, decks) primarily in Chinese and/or English;
  no other input formats beyond DOCX/PDF/PPTX are in scope for this version.
- Default operating parameters follow the constitution and source requirements: soft split limit
  ~1200 characters, input size limit ~50 MB, header/footer repetition threshold ≥2 occurrences.
- The knowledge base is single-tenant / single-service scale (embedded, in-process index) rather
  than a multi-node distributed search cluster; authentication/authorization of agents is out of
  scope for this version (access is via the deployed endpoint).
- The target deployment node is Zeabur Arm Ampere A1 (ARM64, no GPU); model assets are downloaded
  and cached once on that node.
- Development follows an AI-only workflow with semantic commit history and layered automated tests,
  per the constitution; those process obligations are governed by the constitution rather than
  re-specified here.

## Dependencies

- Public deployment platform providing HTTPS and persistent volume storage (e.g. Zeabur).
- Availability of the document-parsing, embedding, and OCR model assets on the ARM64 node.
