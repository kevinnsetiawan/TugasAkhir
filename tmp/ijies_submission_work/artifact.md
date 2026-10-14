# IJIES Submission Manuscript Template Contract

## Reference and verification evidence
- Retained reference: `C:\Users\Kevin Setiawan\Downloads\(Ver. 2026.10.1) IJIES_Format (1).docx`
- Task-local reference copy: `C:\Users\Kevin Setiawan\OneDrive\Desktop\Tugas Akhir\tmp\ijies_submission_work\IJIES_Format_reference.docx`
- SHA-256: `8f4c033348b67518ad1e4dc5429ebc6203212c97a2532b000a7fe9256731c01c`
- A prior render of the same byte-identical template is preserved at `tmp/ijies_article_work/template-reference.pdf` (5 pages). The current packaged renderer was also attempted and reported that `soffice.exe` is not installed.
- Section audit: template has three A4 portrait sections, 8.268 x 11.693 in, margins L/R 0.75 in and T/B 1.00 in. The first is one column; article section uses two columns with 0.472 in gap; the final one-column section contains submission guidance that is not manuscript content.
- Style evidence: `tmp/ijies_submission_work/template-style-evidence.json`; section evidence from packaged `section_audit.py`.

## Page system and flow
- First-page title/author/abstract block is one column and includes the journal masthead image at the top.
- Article body, declarations, and references run in two columns. Page geometry and margins remain A4 portrait, L/R 0.75 in, T/B 1.00 in.
- Submission checklist and award descriptions are removed from the manuscript.
- The existing article draft is already derived from this template and preserves the masthead, two-column section, margins, and typography. It is the editing base; the delivered file is a separate copy.

## Typography and components
- Main title: centered, Times New Roman, 14 pt, bold.
- Author: centered, Times New Roman, 11 pt, bold; affiliation centered, 11 pt regular; corresponding email centered, approximately 10.5 pt.
- Abstract and keywords: Times New Roman, 10 pt, single spaced; abstract no more than 150 words; keyword items separated by commas.
- Main text: Times New Roman, 11 pt, single spaced, justified, first-line indent; heading 1 12 pt bold and heading 2 11 pt bold; captions 10 pt and centered.
- Figure captions belong below figures; table titles belong above tables. Figures and tables use independent sequential numbering.
- Conflict of Interest declaration is mandatory. Author Contributions is required for multiple authors; this manuscript has one author. Acknowledgments are included only for confirmed support.

## Editable slots and content contract
- Preserve title, author name, affiliation, and corresponding email already present in the article draft.
- Update the abstract and keyword punctuation; update graphics and figures to match the current experiment summaries and CSV logs.
- Preserve all accurate methods, tables, and result discussion. Correct only claims that do not match the current result files or the supplied template.
- Add a system workflow figure and a discovery-progress figure; retain the category comparison chart with current values. Remove the obsolete ZAP workflow illustration if it is replaced by the system workflow figure.
- Keep training metrics explicitly in-sample, distinguish payload-level verified actions from unique endpoint-class locations, and qualify the scoped ZAP ratio as descriptive because workflows and request accounting differ.
- Do not invent funding, acknowledgments, author roles, or conflict disclosures.

## Fidelity gates
- Keep the retained template unmodified and byte-identical to the recorded SHA-256.
- Final document must contain no template instructions, author placeholders, unresolved editorial metadata, or stale experimental metrics.
- Preserve A4 geometry, title block, two-column body, masthead, font hierarchy, and required declarations.
- Render and inspect every page before delivery. A render with the packaged tool is currently blocked because LibreOffice is unavailable; use a verified Word rendering path if available.
