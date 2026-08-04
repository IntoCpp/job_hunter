Extract structured job posting fields from HTML or text.

Postings may be in English or French. Detect the primary language of the posting (use ISO 639-1 codes: en or fr). Preserve all extracted text fields in the original language of the posting; do not translate.

Return JSON with keys:
- company
- title
- location
- address
- description
- language

Use null for fields that are not present on the page. Do not invent values.
