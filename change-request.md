# Change Requests

Version: 2

**Status:** Approved for implementation (decisions captured below).

Previous requests:

* All change requests from the 2026-07-30 batch have been implemented.

---

# Change Request – Remove Automated Job Search

## Objective

Refocus the project so that its responsibility begins with a list of job posting URLs provided by the user.

Automatic discovery of job postings is no longer part of the project. The application processes user-provided URLs only.

---

## New Processing Pipeline

```text
Load job search profile + preferences (for ranking only)
↓
Load user job list (company + URL from YAML)
↓
Download job posting
↓
Validate download
↓
Extract structured information
↓
Validate extraction
↓
Rank the job
↓
Save history + artifacts
↓
(Optional) Resume customization
```

**In scope:** everything from the user-provided URL list onward, plus profile/preferences loading required for ranking.

**Out of scope:** Serper, job-board discovery, company-site crawling, search providers, and all configuration tied exclusively to discovery.

---

## Functional Requirements

1. Replace the automated search component with a YAML file listing jobs to process.
2. The file path is configured in `config.yaml` via the `job_postings_file` key.
3. The path may be overridden on the command line with `--url-postings <FILE_PATH>`.
4. Add a sample file at `config/jobs_to_process.yaml.example` for testing and documentation.
5. The orchestrator iterates every entry in the file and processes each URL independently.
6. Existing CLI options unrelated to search (`--config`, `--test`, `--verbose`, `--generate-job-search-profile`, `--skip-resume`, `--max`) continue to work.

---

## Implementation Decisions / Clarifications

These decisions resolve implementation ambiguities and supersede any conflicting text elsewhere in this document.

### CLI option

| Item | Decision |
|------|----------|
| Flag | `--url-postings <FILE_PATH>` |
| Purpose | Override the configured `job_postings_file` path for a single run |

### Configuration key

| Item | Decision |
|------|----------|
| Key | `job_postings_file` (top-level in `config.yaml`, consistent with existing flat config layout) |
| Example | `job_postings_file: "./config/jobs_to_process.yaml"` |

### Company name handling

| Item | Decision |
|------|----------|
| Authority | User-provided `company` from the input YAML always wins |
| Extraction | If the extractor returns a company name, store it as metadata (e.g. `extracted_company`) but do **not** replace `posting.company` |
| Failed extraction | Keep the user-provided company even when extraction fails (do not use `Extraction Failed` as the company name when the user supplied one) |

### History `source` field

| Item | Decision |
|------|----------|
| Remove | Search-related values (`serper`, `company:domain`, job-board sources, etc.) |
| Use | `source: user_input` in history metadata |
| Company | Remains a separate field on the history entry (`company`), not nested under `source` |

Example metadata on an accepted entry:

```yaml
company: "Example Corporation"
metadata:
  source: user_input
  extracted_company: "Example Corp Inc."   # optional, when extraction differs
  extraction_status: SUCCESS
  language: en
```

### Configuration cleanup

| Item | Decision |
|------|----------|
| `models.agent` | Remove from config classes, YAML examples, and tests (unused) |
| `web_sites`, `search` | Remove entirely |
| `SERPER_API_KEY` | Remove from `.env.example` and runtime requirements |
| Compatibility | No compatibility layers for removed search functionality (preserved on `job_search_experiment` branch) |

### Profile generation

| Item | Decision |
|------|----------|
| Keep | `--generate-job-search-profile` and `ProfileService` |
| Reason | Generated profile is still required for ranking |
| Change | Profile is no longer used to build web search queries |

---

## Job URL Input File Format

YAML file referenced by `job_postings_file`.

Example (`jobs_to_process.yaml`):

```yaml
jobs:
  - company: "Example Corporation"
    url: "https://example.com/careers/software-development-manager"

  - company: "Another Company"
    url: "https://another-company.com/jobs/senior-software-lead"

  - company: "Government Organization"
    url: "https://government.example/jobs/team-lead"
```

| Field | Required | Description |
|-------|----------|-------------|
| `company` | Yes | Authoritative company name for history, artifacts, and pipeline |
| `url` | Yes | Job posting URL to download and process |

Title, location, description, and other posting details are extracted from the downloaded page — not required in this file.

---

## Code Cleanup

Remove all code, configuration, prompts, tests, and documentation that exist **solely** to support automated job searching:

- `src/job_hunter/tools/search/` (entire package)
- Search-related config models (`WebSitesConfig`, `CompanySite`, `JobBoard`, `SearchConfig`)
- `build_search_titles()` and other search-only helpers
- Search-related tests
- `SERPER_API_KEY` usage

**Keep** (not search-specific):

- Download (`DownloadTool`, `BrowserTool`)
- Download validation (`page_validation_service`)
- Extraction, ranking, history, artifacts, resume tools
- Profile and preferences services (ranking inputs)
- LLM service and non-search prompts (`extract_posting`, `rank_posting`, `location_filter`, `job_search`)

Remove obsolete code rather than commenting it out. Run `uv run pytest` after each major refactoring step.

Remove unused Python packages from `pyproject.toml` if any become unused (Serper used `httpx` directly — no dedicated Serper package expected).

---

## Documentation

Update `requirements.md`, `design.md`, and `README.md` to describe:

- New project scope (URL-list-driven, not discovery-driven)
- `job_postings_file` configuration
- `--url-postings` CLI option
- Updated pipeline diagram
- Removal of Serper/search configuration

---

## Non-Goals

Do not redesign these components except where necessary to remove search dependencies or apply the clarifications above:

| Component | Expected change |
|-----------|-----------------|
| Downloader | None |
| Download validation | None |
| Extraction | Wire user `company`; store `extracted_company` metadata when applicable |
| Extraction validation | None |
| Ranking | None |
| History | `source` semantics only |
| Resume customization | None |

---

## Acceptance Criteria

- [ ] No automated job search functionality remains.
- [ ] Application loads jobs from a YAML file (`jobs` list with `company` + `url`).
- [ ] Path configurable via `job_postings_file` in `config.yaml`.
- [ ] Path overridable via `--url-postings <FILE_PATH>`.
- [ ] User-provided company preserved through the pipeline (including failed extractions).
- [ ] History metadata uses `source: user_input`.
- [ ] Download, extraction validation, ranking, history, and resume customization continue to function.
- [ ] `models.agent`, `web_sites`, and `search` removed from configuration.
- [ ] Documentation updated.
- [ ] Applicable tests pass; search-only tests removed; new job-list loading tests added.
- [ ] Sample file `config/jobs_to_process.yaml.example` added.

---

## Implementation Plan (for developer)

### Phase 1 — Add job list input

- Add `JobToProcess` model and `job_list_service` to load/validate YAML.
- Add `job_postings_file` to `AppConfig` and `configuration_service`.
- Add `config/jobs_to_process.yaml.example` and unit tests.

### Phase 2 — Rewire orchestrator

- Replace `SearchTool` with job list loading in `JobHunterAgent.run()`.
- Pass user `company` through `_process_url`; set `source` to `user_input`.
- Add `--url-postings` to CLI.
- Remove `SERPER_API_KEY` requirement.

### Phase 3 — Remove search code

- Delete `tools/search/` and search-only tests/helpers.
- Remove search config from YAML examples and config models.

### Phase 4 — Docs and final verification

- Update `requirements.md`, `design.md`, `README.md`.
- Full test run and implementation report.

---

## Final Report

At the end of implementation, provide:

- Files removed
- Files added
- Configuration changes
- Dependencies removed
- Tests added or modified
- Architectural decisions made during cleanup
