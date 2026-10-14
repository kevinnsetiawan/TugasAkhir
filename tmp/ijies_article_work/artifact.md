# IJIES Manuscript Template Contract

## Reference
- Source: `C:\Users\Kevin Setiawan\Downloads\(Ver. 2026.10.1) IJIES_Format.docx`
- SHA-256: `8f4c033348b67518ad1e4dc5429ebc6203212c97a2532b000a7fe9256731c01c`
- Section count: 3; A4 portrait, 8.268 x 11.693 in; margins L/R 0.75 in, top/bottom 1.00 in.
- Render: packaged LibreOffice renderer unavailable (`soffice.exe` not found). Microsoft Word installed; hidden Word rendering requested for approval. Page count and visual evidence unresolved until render completes.
- Audits: `section_audit.py`, `style_lint.py`; evidence in `template-style-evidence.json`.

## Page system and content flow
- Section 1: one column; title and author block, abstract (max 150 words), keywords; top logo image retained.
- Section 2: two columns, 0.472 in column spacing; main article, declarations, and references.
- Section 3: one column; template's submission instructions and award information are not part of the manuscript and will be removed. Merge into the two-column manuscript section, preserving page geometry and recurring components.
- Three inline images: top-page journal logo (preserve), two sample-figure images embedded in template guidance (remove and replace only with article figures if used). One sample table (remove).
- Header contains placeholder received/revised dates; footer contains placeholder issue/DOI and license language. Remove unassigned editorial metadata; retain footer/header geometry and existing page furniture where applicable.

## Typography and recurring components
- Main title: centered, Times New Roman, 14 pt, bold.
- Author names: centered, Times New Roman, 11 pt, bold; affiliation centered, 11 pt regular; corresponding email centered, about 10.5 pt.
- Abstract and keywords: Times New Roman, 10 pt, single-spaced; abstract <=150 words; horizontal rules around abstract/keyword block as in source.
- Body: Times New Roman, 11 pt, single-spaced, fully justified, first-line indent about 1.5 character widths; no extra blank paragraph gaps.
- First-order heading: left aligned, 12 pt bold; second-order heading: left aligned, 11 pt bold. Captions/table titles 10 pt, centered; tables/figures numbered sequentially. References: numbered in first-citation order, IJIES style.
- Conflict of Interest declaration mandatory; Author Contributions applies only if multiple authors. Acknowledgments only when support is confirmed.

## Edit slots
- Keep and replace: paragraph 1 title; paragraph 3 author line; paragraphs 5-7 affiliation/email; paragraph 10 abstract; paragraph 11 keywords.
- Preserve first section break after paragraph 14 (title block to two-column body).
- Replace template guidance/example body with article sections, tables, figures as supported by source material, declarations, and numbered references.
- Remove sample instructions, sample figure/table examples, submission conditions, award descriptions, and unresolved journal publication metadata.
- Author: Kevin Imanuel Setiawan; affiliation derived from thesis cover as Bachelor's Program in Information Technology, Telkom University, Surabaya, Indonesia; email: kevinit@student.telkomuniversity.ac.id.

## Package preservation and fidelity gates
- Preserve source styles, numbering, theme, custom XML, relationships, top logo, section/page geometry, and unrelated package parts. Prefer patching only `word/document.xml` and intended header/footer text parts.
- No content controls identified in the initial paragraph/table inventory. A deeper package comparison and field audit remain required before final delivery.
- Final article text in English; claims and metrics sourced from the latest thesis PDF unless explicitly reconciled with project artifacts. Avoid unsupported declarations; author must confirm conflict-of-interest and funding statements.
- Required before delivery: render final DOCX, inspect every rendered page at 100%, compare template/final page geometry and package parts, remove remaining placeholders, and note any unresolved data mismatch.
