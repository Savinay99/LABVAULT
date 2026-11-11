---
name: create-polished-pdf
description: Use when creating, revising, converting, or quality-checking a PDF where page layout, typography, tables, forms, citations, or reliable printing matter.
---

# Create polished PDFs

Make PDFs that are accurate, readable on screen, and reliable when printed. Treat the supplied text, data, and references as the source of truth; never invent missing facts, numbers, citations, observations, or institutional branding.

## Before creating

1. Identify the reader, purpose, delivery context, and whether this is a new document or an edit to an existing PDF.
2. Preserve user-provided wording and data unless editing is requested. Resolve obvious formatting noise without changing meaning; flag ambiguities that affect correctness.
3. Use supplied brand assets and samples. If none are supplied, choose a restrained, consistent visual system and avoid fabricated logos or seals.
4. Select page size, margins, orientation, language, and accessibility needs. Default to A4 for academic/international documents and US Letter for US contexts; follow a supplied template when present.
5. Choose a source format suited to the work (for example, DOCX/HTML for reflowing prose, a vector/layout library for generated reports, or direct PDF editing for narrowly scoped changes). Avoid rasterizing text-heavy pages.

## Layout and content

- Establish a clear type hierarchy, readable body size, consistent spacing, aligned margins, and adequate contrast.
- Use real headings, lists, tables, hyperlinks, page numbers, and document metadata where applicable. Keep repeated headers and table headings consistent across pages.
- Keep each table column readable; allow rows and paragraphs to continue safely across pages. Avoid clipping, overlapping, accidental blank pages, stranded headings, tiny type, and excessive empty space.
- Check table row counts, labels, units, and continuation when these are specified. Make tables usable for their purpose: leave writing space for paper forms and optimize for scanning when the PDF is screen-first.
- Keep equations, units, symbols, and source notation faithful. Embed or subset fonts when the chosen tool supports it; check special characters in the rendered output.
- Preserve searchable/selectable text. Add tags, logical reading order, link labels, and alt text when supported and relevant. Do not claim PDF/UA or accessibility compliance without a dedicated validation pass.
- For forms, confirm field names, tab order, input types, and whether the recipient needs fillable fields. Never flatten an existing form unless requested.
- For signed, secured, or archival PDFs, preserve the source and explain any transformation that invalidates signatures, encryption, or archival properties.
- Cite sources next to claims or in a compact references section. Verify references against supplied or authoritative sources; never fabricate them.
- Check that each citation maps to a reference and that supplied bibliographic details are internally consistent. Flag missing details instead of guessing them.

## Verify before delivery

1. Export the PDF and render every page to images at a readable resolution.
2. Inspect all pages, including dense tables, first/last pages, page breaks, headers, footers, and any page containing formulas or unusual glyphs. Fix layout defects and render again.
3. Check page count and dimensions; extract text to detect missing, reordered, or truncated content; verify required table row counts and equation numbering/cross-references; check links and form fields when present.
4. Confirm the output opens in a standard viewer and that fonts and symbols render. If a conversion tool emits warnings, distinguish tool/environment warnings from actual PDF defects.
5. Report the deliverable, verification performed, and any known limitations. Link the final file. Do not claim unperformed checks.

## Safety and scope

- Do not upload private or sensitive source material to an external converter or service unless the user has authorized that specific destination.
- Do not overwrite the only copy of a source PDF; create a separate output unless the user explicitly requests replacement.
- Do not add a cover, logo, signature, or decorative illustration that changes the document's implied authorship or authority.
