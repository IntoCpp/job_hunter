# Design

**Project:** Job-Hunter

**Version:** 0.9

---

# 1. Design Authority

`requirements.md` is the authoritative source describing **what** the software must do.

This document is the authoritative source describing **how** the software is implemented.

Any implementation decision that conflicts with this document shall first be reviewed and the design updated before changing the implementation.

---

# 2. Design Goals

The project is designed around the following principles:

* Simplicity over unnecessary complexity.
* Modular architecture.
* Small, focused components.
* Easily testable components.
* AI used only where it provides clear value.
* Easy replacement of individual tools.
* Future compatibility with MCP services.
* Minimize AI token consumption.
* Prefer deterministic logic over AI reasoning when possible.

---

# 3. Technology Stack

## Language

* Python

## Development

* Cursor (AI-assisted development)
* Visual Studio Code (primary code editor)

## Environment

* Windows
* uv

## AI Framework

* OpenAI Agents SDK

## Browser Automation

* Playwright (fallback when HTTP download is insufficient)

## Credentials

* `.env` file at project root (excluded from version control)
* Expected keys: `OPENAI_API_KEY`

## Future Technologies

The following are intentionally excluded from the first implementation:

* Docker
* MCP services
* Distributed services

The architecture shall nevertheless allow these technologies to be introduced later with minimal changes.

---

# 4. High-Level Architecture

```text
                    JobHunter Agent
                           │
              ┌────────────┴────────────┐
              │                         │
    Job Search Profile Tool    Job Postings File
      (generate / load cache)   (company + URL list)
              │                         │
              └────────────┬────────────┘
                           │
              Processing Tools (download, extract, rank)
                           │
                     Resume Rework
```

The JobHunter Agent is responsible for orchestration.

Job search criteria come from two separate sources:

* A cached **job search profile** (`job_search_profile.yaml`), AI-generated from resume input files.
* A user-maintained **job search preferences** file (`my_job_preferences.yaml`), configured via `search_profile.job_search_preferences.file`.

Business logic shared by multiple tools resides in `services/`. Tool-specific logic resides in `tools/`.

### Data Flow

```text
search_profile.input_files                search_profile.output_file
(resume, analysis, LinkedIn)         →   job_search_profile.yaml (AI cache)
                                                    │
search_profile.job_search_preferences.file          │
(my_job_preferences.yaml)              →            │
                                                    ▼
                                          JobHunter Agent
                                                    │
                              ┌─────────────────────┼─────────────────────┐
                              ▼                     ▼                     ▼
                     Job List Loader         Download Tool         Ranking Tool
                   (job_postings_file)       (URL → content)   (profile + preferences)
                              │                     │                     │
                              └─────────────────────┼─────────────────────┘
                                                    ▼
                                          posting_output / history
```

---

# 5. Project Structure

```text
job-hunter/

├── README.md
├── requirements.md
├── design.md
├── pyproject.toml
├── .env                          # API keys (not in version control)
├── .gitignore
├── config/
│   ├── config.yaml               # Production configuration
│   └── my_job_preferences.yaml   # User-maintained job search preferences
├── .test/
│   └── config.yaml               # Test/development configuration
│
├── src/
│   └── job_hunter/
│       ├── agent/                # Orchestration logic
│       ├── tools/                # Individual capabilities
│       ├── services/             # Reusable business logic
│       ├── models/               # Data structures
│       └── utils/                # Generic helper functions
│
├── tests/
│   └── test_data/                # Reusable test fixtures
│
└── test/                         # Local test assets (some gitignored)
    ├── master_resume.md                      # Production sample (gitignored)
    └── master_resume_analysis_cache.json     # Production sample (gitignored)
```

## Folder Responsibilities

| Folder | Responsibility |
|--------|---------------|
| `agent/` | Orchestration — coordinates workflow and tool execution |
| `tools/` | Individual capabilities (search, download, extract, rank, etc.) |
| `services/` | Reusable business logic shared by tools or agents |
| `models/` | Internal data structures |
| `utils/` | Generic helper functions with no business knowledge |

## services/ Package

The `services/` package contains reusable business logic shared by multiple tools or agents. It is **not** an enterprise service layer or abstraction layer.

Good candidates:

* `ranking_service.py`
* `history_service.py`
* `filename_service.py`
* `configuration_service.py`
* `profile_service.py`
* `preferences_service.py`

A service should exist only when it encapsulates reusable business logic that provides clear value.

Avoid unnecessary indirection:

```text
SearchTool → SearchService → SearchRepository → SearchManager → SearchProvider
```

when each layer only forwards calls.

---

# 6. Architectural Philosophy

The project follows a tool-oriented architecture.

Each capability shall exist as an independent module with a clearly defined interface.

Examples:

* Generate job search profile (AI-derived search criteria)
* Load user job postings file
* Download job postings
* Extract job information
* Rank postings
* Save history
* Call resume customization script

Tools shall not directly depend on each other.

The JobHunter Agent coordinates tool execution.

Tools shall be designed so implementations can later be replaced by external services, including MCP-backed services.

---

# 7. Agents

Version 1 uses a single primary AI agent for orchestration (JobHunter Agent).

The JobHunter Agent responsibilities:

* Load configuration.
* When `--generate-job-search-profile` is set, run profile-only mode and exit.
* Otherwise, ensure the job search profile is available (load cache or generate if missing).
* Coordinate workflow execution.
* Select and call tools.
* Make AI-assisted decisions when required.
* Generate execution summaries.

### Job Search Profile Generation

Profile generation is a **separate capability** (implemented as a dedicated tool and/or agent). It is not embedded in the main orchestration logic.

Responsibilities:

* Read configured `search_profile.input_files`.
* Invoke an LLM to analyze resume information and produce structured search criteria.
* Write the result to `search_profile.output_file` (`job_search_profile.yaml`).
* Support future additional input sources (LinkedIn profile, manual preferences) without architectural changes.

Cache rules (v1):

* Generate only when the output file does not exist.
* User deletes the cache file to trigger regeneration.
* No automatic regeneration based on input file timestamps or content changes.

Future versions may introduce specialized agents.

### Model Selection

Model identifiers are configuration-driven and not part of the architecture. The configuration defines two model sets: `models_test` (selected when `--test` is passed) and `models_prod` (default). Each set provides `profile`, `ranking`, `location`, and `extraction` identifiers. Models may be adjusted based on quality, speed, and cost.

| Use case | Model strategy |
|----------|---------------|
| Agent orchestration | Cost-effective model |
| Job search profile generation | Cost-effective model |
| Ranking | More capable model when accuracy is important |
| Location matching | Cost-effective model |
| Extraction (difficult cases) | Configurable per operation |

---

# 8. Tools

## 8.1 Job Search Profile Tool

Generates and loads the cached job search profile.

### Generation

Input: files listed in `search_profile.input_files` (resume, resume analysis, optional LinkedIn profile).

Output: `job_search_profile.yaml` written to `search_profile.output_file`.

Uses an LLM to analyze the input files and produce structured search criteria (target titles, equivalent titles, skills, seniority, exclusions, etc.). The generation prompt requests bilingual English/French titles and keywords where appropriate for the candidate's job market.

This tool does **not** read or modify `my_job_preferences.yaml`.

### Cache behavior

| Mode | Behavior |
|------|----------|
| Full run, cache exists | Load cached profile (preserves manual edits) |
| Full run, cache missing | Generate via LLM, write cache |
| `--generate-job-search-profile` | Always regenerate via LLM, overwrite cache, then exit |

No timestamp- or content-based auto-regeneration in v1.

### Profile-only mode

When `--generate-job-search-profile` is passed:

1. Load configuration.
2. Regenerate profile (overwrite existing cache).
3. Write `search_profile.output_file`.
4. Exit — no search, download, extraction, ranking, or resume rework.

This allows the user to review and manually edit the profile before a full run.

### Consumption

The JobHunter Agent and Ranking Tool consume the loaded profile **and** user job search preferences.

## 8.1.1 User Job Search Preferences

Loaded from the path configured in `search_profile.job_search_preferences.file` (default: `config/my_job_preferences.yaml`).

Responsibilities (`preferences_service.py`):

* Load and validate the YAML preferences file.
* Provide preferred, acceptable, and excluded roles to ranking.
* Serialize preferences for LLM ranking prompts.

The preferences file must exist at startup. It is user-maintained and never overwritten by the system.

## 8.2 Job Postings Loader

Loads the user-provided YAML file configured via `job_postings_file`.

Each entry contains:

* `company` — authoritative company name preserved through the pipeline
* `url` — job posting URL to download and process

The path may be overridden per run with `--url-postings <FILE_PATH>`.

Implemented in `job_list_service.py`. Sample format: `config/jobs_to_process.yaml.example`.

## 8.3 Browser Automation Tool

Playwright-based fallback for websites that:

* Require JavaScript execution.
* Dynamically load content.
* Require navigation or interaction.

Implemented behind a dedicated tool interface to allow future replacement (including MCP-based services).

## 8.3.1 Browser Session Fallback Tool

CDP-based fallback for pages that block headless HTTP or Playwright retrieval.

* Connects to a **running** Edge or Chrome instance started with remote debugging enabled.
* Default endpoint: `http://127.0.0.1:9222` (configurable via `browser_session.debug_host` and `debug_port`).
* Job-Hunter does **not** launch the user's browser; the CLI prompts for confirmation before processing.
* Optional fallback: explicit `browser_session.browsers` entries with a dedicated `user_data_dir` only (never the live default profile).
* Firefox is not supported for browser session fallback.

## 8.4 Download Tool

Retrieves job posting content from a user-provided URL using a modular multi-step strategy implemented in `PostingRetrievalService`.

Strategy:

1. HTTP request (preferred)
2. Playwright browser automation when HTTP retrieval or validation fails
3. Browser session via CDP connect when Playwright retrieval or validation fails

Each step validates the downloaded page before accepting it. The successful retrieval method (`http`, `playwright`, or `browser_session`) is recorded in posting history metadata and saved posting artifacts.

Input: URL from the job postings file

Output: Retrieved page content

## 8.5 Extraction Tool

Extracts structured information from a posting.

Expected information:

* Company
* Job title
* Location
* Address
* Description
* Language (primary language of the posting: `en` or `fr`)

The LLM prompt instructs the model to detect the posting language and preserve all extracted text in the original language without translation.

## 8.5.1 Language Support

Job postings may be in English or French. Language handling applies across the pipeline:

| Stage | Behavior |
|-------|----------|
| Extraction | Detect language (`en`/`fr`); preserve original-language text fields |
| Profile generation | Include bilingual titles and keywords for the search market |
| Search | Build queries from bilingual profile criteria |
| Location matching | Accept location text in English or French |
| Ranking | Score fit across languages; interpret equivalent titles (e.g. *Directeur de développement logiciel* ≈ *Software Development Manager*) |
| Saved Markdown | Store description and fields in original language; include language metadata |

Supported language codes: `en`, `fr`. The `language` field is stored on `JobPosting` and recorded in posting history metadata when available.

## 8.6 Ranking Tool

Hybrid approach combining deterministic filtering and LLM-based semantic evaluation.

Inputs:

* Job posting (extracted data)
* Job search profile (cached YAML)
* User job search preferences (`my_job_preferences.yaml`)
* Original resume sources from `search_profile.input_files` (as needed)

### Deterministic Filtering (before LLM)

* Location filtering (AI-assisted interpretation of human-readable location definitions)
* Duplicate detection (company + title + location)
* Excluded companies or job types (from job search profile)
* Excluded roles (from user preferences)

### LLM Semantic Evaluation

* Resume/job fit (using profile and resume sources)
* Equivalent experience
* Similar responsibilities
* Company-specific terminology
* Job title interpretation (using profile target and equivalent titles)
* Cross-language equivalence (English and French postings evaluated against bilingual profile criteria)
* Alignment with user preferred and acceptable roles; penalty for conflict with excluded roles

### Output

```text
confidence = 0.00 – 1.00
```

The final ranking score is generated by the LLM.

## 8.7 History Tool

Maintains processed job posting history in a dedicated history directory:

* `accepted_postings.yaml`
* `rejected_postings.yaml`
* `failed_downloads.yaml`
* `failed_extractions.yaml`

Legacy single-file `posting_history.yaml` paths are migrated automatically on first load.

Responsibilities:

* Duplicate detection (company + title + location) on accepted postings only
* History updates (including `date_last_seen` on duplicate encounter)
* Metadata storage (extraction status, source, language, failure reasons)

When a duplicate is detected, `date_last_seen` is updated and further processing for that posting is skipped.

Failed downloads and extractions record URL, date, failure reason, source, company (when available), and retrieval attempts for later inspection.

When all retrieval methods fail, the orchestrator prints a visible CLI summary listing failed download artifact paths. Retrieval failures are recorded in `failed_downloads.yaml` and `posting_output/failed_downloads/`.

## 8.8 Resume Tool

Invokes the external resume customization script.

| Property | Value |
|----------|-------|
| Script | `C:\Users\ERIC\Documents\Code\job-hunter-resume-rework\resume_rework.py` |
| Working directory | `C:\Users\ERIC\Documents\Code\job-hunter-resume-rework\` |
| Required argument | `--job-posting <path_to_saved_markdown>` |
| Invocation | Fire-and-forget (subprocess, do not wait) |
| Invocation command | `uv run resume_rework.py --job-posting <path>` |

The script is a separate project. Job-Hunter shall never modify files in that project.

A unit test shall verify invocation using a dummy job posting in the test folder.

---

# 9. Internal Models

## JobPosting

* Title
* Company
* Location
* URL
* Markdown filename
* Confidence score
* Description
* Language (ISO 639-1 code: `en` or `fr`)

## JobSearchProfile

Loaded from generated cache file (`job_search_profile.yaml`).

Contains AI-derived search criteria. See Section 18 for the field schema.

## JobSearchPreferences

Loaded from user-maintained `my_job_preferences.yaml` (path configured in `search_profile.job_search_preferences.file`).

Contains explicit user role preferences. See Section 20 for the field schema.

## ResumeAnalysis

Loaded from JSON (input file referenced in `search_profile.input_files`).

See Section 21 for the field schema.

## Configuration

Loaded from YAML.

See Section 17 for the schema.

## PostingHistoryEntry

* Company
* Job title
* Location
* URL
* Date first found
* Date last seen
* Ranking score
* Path to Markdown description
* Additional metadata (when reasonably small)

---

# 10. Workflow

## 10.1 Full Run

```text
Load Configuration

↓

Load Job Search Profile (generate only if cache missing)

↓

Load User Job Search Preferences (my_job_preferences.yaml)

↓

Load Job Postings (job_postings_file)

↓

Filter duplicates (update date_last_seen, skip known postings)

↓

Download

↓

Validate Download (block pages, search results, login/CAPTCHA, etc.; retry with next retrieval method on failure)

↓

Extract

↓

Validate Extraction (company, title, description required)

↓

Deterministic filtering (location, profile exclusions, user excluded roles)

↓

LLM ranking (using profile + preferences + resume sources; skipped when extraction failed)

↓

Save posting artifacts (markdown, raw HTML, extraction.json, ranking.json)

↓

Update history (accepted / rejected / failed downloads / failed extractions)

↓

Run resume customization (fire-and-forget, if confidence ≥ threshold and not `--skip-resume`)

↓

Generate summary
```

## 10.2 Profile-Only Run (`--generate-job-search-profile`)

```text
Load Configuration

↓

Regenerate Job Search Profile (overwrite cache)

↓

Exit
```

If `--generate-job-search-profile` is present, the full run workflow (Section 10.1) is not executed.

The workflow shall provide enough runtime information for a user to understand the current operation.

When the `--test` flag is passed, processing stops after two **new accepted** postings and verbose logging is automatically enabled.

`--max N` stops after `N` new accepted postings. `--skip-resume` runs the full workflow without invoking resume customization.

---

# 11. Error Handling

Errors should be recoverable whenever possible.

Failure to process one posting shall not terminate the complete execution.

Errors shall include enough context for troubleshooting.

---

# 12. Logging and Runtime Information

The application uses two log levels:

## Normal

Default logging level.

Provides:

* Major workflow steps
* Progress information
* Important warnings
* Errors

Example (full run):

```text
Loading configuration...
Loading job search profile...
Searching job sources...
Found 25 postings.
Filtering duplicates...
Ranking jobs...
Saving results...
Completed.
```

Example (profile-only run):

```text
Loading configuration...
Generating job search profile...
Job search profile saved to job_search_profile.yaml
Completed.
```

## Debug

Debug logging is enabled when either:

* The user passes `--verbose` on the command line, or
* The user passes `--test` on the command line.

Passing `--test` automatically enables verbose logging in addition to limiting processing to two postings. This verbose-in-test-mode coupling is hardcoded and cannot be overridden.

Test mode is **not** enabled by default; it requires the `--test` flag.

Debug logging may include:

* Function execution details.
* Input parameters when useful.
* Operation results.
* External calls.
* Intermediate processing information.
* Additional diagnostic information.

## Log Output

Each execution shall generate a log file.

Log files shall be stored in the configured output folder.

Example:

```text
posting_output/
└── logs/
    └── 2026-07-27_143100.log
```

The log file shall contain sufficient information to understand the execution flow and diagnose problems.

Log output shall contain timestamps with date.

---

# 13. Testing Strategy

Testing is a required part of development.

The project uses:

* Pytest
* uv for execution

Tests are executed using:

```bash
uv run pytest
```

Each significant function shall have unit tests.

Tests should cover:

* Normal usage cases.
* Boundary conditions.
* Invalid or unexpected inputs.
* Failure cases.

When handling external or user-provided data, tests should consider:

* Empty values.
* Malformed strings.
* Unexpected characters.
* Escape characters.
* Invalid formats.

Tests should be deterministic whenever practical.

### Test Configuration

Tests use `.test/config.yaml` instead of `config/config.yaml`.

Reusable test fixtures are stored under `tests/test_data/`.

An anonymized copy of `test/master_resume.md` and `test/master_resume_analysis_cache.json` shall be created for tests (production samples are gitignored).

### Required Unit Tests

* Filename collision-resolution algorithm (`_a` … `_z`, `_aa`, `_ab`, …)
* Resume script invocation (fire-and-forget, dummy posting)
* Job search profile cache behavior (generate when missing on full run, load when present, regenerate and overwrite with `--generate-job-search-profile`)
* Job search preferences loading (valid file, missing file, invalid schema, workflow integration)

---

# 14. AI Usage

The LLM shall be used only where deterministic logic is insufficient.

Good AI usage:

* Generating the job search profile from resume information.
* Ranking job postings (semantic evaluation).
* Understanding equivalent job titles.
* Interpreting locations.
* Extracting difficult information.

Avoid AI usage for:

* File operations.
* Configuration loading.
* Cache existence checks.
* Duplicate detection.
* Sorting.
* Simple data transformations.
* Filename collision resolution.

---

# 15. Future Enhancements

Possible future enhancements:

* MCP-backed tools.
* Docker deployment.
* Multiple specialized AI agents.
* Persistent database.
* Embedding-based search.
* Automatic scheduling.
* Web dashboard.
* Statistics and reporting.
* Notifications.
* Structured geographic data (postal codes, coordinates) for location matching.
* Automatic job search profile regeneration when input files change.
* Additional search providers (Bing, Brave).

These enhancements shall not require major architectural changes.

---

# 16. Design Principles

The following principles guide implementation:

* Keep modules small.
* Prefer composition over inheritance.
* Avoid premature optimization.
* Avoid unnecessary abstraction.
* Prefer deterministic code over AI reasoning.
* Keep AI prompts maintainable and separated when practical.
* Add logging for important workflow operations.
* Design components for replacement and testing.

---

# 17. Configuration Schema

```yaml
# ── Paths ──────────────────────────────────────────────────────────
posting_output: "C:\\Users\\ERIC\\Documents\\job_hunter_finds\\"
posting_history: "C:\\Users\\ERIC\\Documents\\job_hunter_finds\\posting_history.yaml"
job_postings_file: "./config/jobs_to_process.yaml"

# ── Job search profile (AI-generated cache) ──────────────────────
search_profile:
  input_files:
    - "C:\\path\\to\\master_resume.md"
    - "C:\\path\\to\\master_resume_analysis_cache.json"
    - "C:\\path\\to\\LinkedIn_profile.md"                    # optional
  output_file: "C:\\path\\to\\job_search_profile.yaml"
  job_search_preferences:
    file: "./config/my_job_preferences.yaml"

# ── Resume customization script ────────────────────────────────────
resume_rework:
  script_path: "C:\\Users\\ERIC\\Documents\\Code\\job-hunter-resume-rework\\resume_rework.py"
  working_directory: "C:\\Users\\ERIC\\Documents\\Code\\job-hunter-resume-rework"

# ── Thresholds ───────────────────────────────────────────────────
confidence_resume: 0.90

# ── AI models (OpenAI model identifiers) ─────────────────────────
# models_test is used when running with --test; models_prod is the default.
models_test:
  profile: "gpt-4o-mini"
  ranking: "gpt-4o-mini"
  location: "gpt-4o-mini"
  extraction: "gpt-4o-mini"

models_prod:
  profile: "gpt-4o"
  ranking: "gpt-4o"
  location: "gpt-4o-mini"
  extraction: "gpt-4o-mini"

locations:
  - name: "Montreal Greater Area"
    guidance: "Montreal and surrounding areas accessible by public transport or reasonable commute"
  - name: "South Shore"
    guidance: "Longueuil, Brossard, Saint-Hubert, and nearby cities"

# Optional browser session fallback (Edge/Chrome only; Firefox is not supported)
browser_session:
  debug_host: "127.0.0.1"
  debug_port: 9222
  # Optional persistent-profile fallback; user_data_dir must be a dedicated profile path.
  browsers:
    - type: edge
      executable: ""
      user_data_dir: ""
```

### CLI Override

```text
uv run job-hunter --config .test/config.yaml
uv run job-hunter --test
uv run job-hunter --generate-job-search-profile
```

| Flag | Effect |
|------|--------|
| `--config PATH` | Configuration file path (default: `config/config.yaml`) |
| `--generate-job-search-profile` | Regenerate job search profile only; overwrite cache; exit (no search or other steps) |
| `--test` | Enable test mode: use `models_test`, limit to 2 postings, and automatically enable verbose |
| `--verbose` | Enable debug logging (redundant when `--test` is also passed, since `--test` always enables verbose) |

---

# 18. Job Search Profile YAML Schema

The generated cache file (`job_search_profile.yaml`) is produced by the Job Search Profile Tool and consumed by the JobHunter Agent and Ranking Tool.

The exact structure may evolve as the LLM output is refined, but the profile shall include the following categories of information:

### Expected Fields

| Field | Type | Description |
|-------|------|-------------|
| `target_titles` | string[] | Primary job titles to search for |
| `equivalent_titles` | string[] | Alternative titles describing similar positions |
| `job_descriptions` | object[] | Role descriptions with title and responsibilities |
| `skills` | string[] | Relevant skills and technologies |
| `seniority_level` | string | Expected seniority (e.g. "senior", "manager", "lead") |
| `preferred_industries` | string[] | Target industries (if applicable) |
| `excluded_titles` | string[] | Job types or titles to avoid |
| `excluded_companies` | string[] | Companies to exclude (may also come from additional profile information) |
| `search_keywords` | string[] | Additional keywords useful for search queries |
| `summary` | string | Brief narrative of the candidate's target role |

### job_descriptions[] Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Job title |
| `description` | string | Role description and key responsibilities |

### Example (illustrative)

```yaml
target_titles:
  - "Software Development Manager"
  - "Software Engineering Manager"
equivalent_titles:
  - "Engineering Manager"
  - "Development Team Lead"
  - "Software Team Lead"
job_descriptions:
  - title: "Software Development Manager"
    description: "Leadership role managing software development teams, delivery, and engineering practices"
skills:
  - "Python"
  - "C++"
  - "Agile"
  - "CI/CD"
seniority_level: "manager"
preferred_industries:
  - "Rail transport"
  - "Embedded systems"
excluded_titles:
  - "Junior Developer"
  - "Intern"
search_keywords:
  - "engineering manager"
  - "software delivery"
summary: "Senior engineering leader seeking management roles in software development and quality."
```

### additional_profile_information.yaml (optional input)

Deprecated for job-search role preferences. Use `my_job_preferences.yaml` instead (configured via `search_profile.job_search_preferences.file`).

---

# 20. User Job Search Preferences YAML Schema

The user-maintained preferences file (`my_job_preferences.yaml`) is loaded at runtime and consumed by the Ranking Tool. It is separate from the AI-generated `job_search_profile.yaml`.

### Expected Fields

| Field | Type | Description |
|-------|------|-------------|
| `preferred_roles` | object[] | Roles the user wants to prioritize |
| `acceptable_roles` | object[] | Roles the user will consider |
| `excluded_roles` | object[] | Roles the user wants to avoid |

### preferred_roles[] Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Role title (required) |
| `priority` | integer | Priority rank (lower number = higher priority) |
| `description` | string | Why this role is preferred |

### acceptable_roles[] / excluded_roles[] Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Role title (required) |
| `description` | string | Clarifies the role scope |

### Example

```yaml
preferred_roles:
  - title: "Software Development Manager"
    priority: 1
    description: "Management role leading software development teams."

acceptable_roles:
  - title: "Software Team Lead"
    description: "Technical leadership role with software development responsibilities."

excluded_roles:
  - title: "Senior Software Developer"
    description: "Individual contributor role without management responsibilities."
```

---

# 21. Resume Analysis JSON Schema

The `resume_analysis` file is JSON (not YAML). Field schema derived from the production sample:

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `full_name` | string | Candidate name |
| `location` | string | Primary location |
| `headline` | string | Professional headline |
| `executive_profile` | string | Summary paragraph |
| `years_experience` | integer | Total years of experience |
| `preferred_positioning` | string[] | Target job titles |
| `avoid_positioning` | string[] | Titles to avoid |
| `core_competencies` | string[] | Core competency list |
| `technical_skills` | string[] | Technical skills |
| `leadership_skills` | string[] | Leadership skills |
| `methodologies` | string[] | Methodologies and practices |
| `certifications` | string[] | Certifications |
| `experience` | object[] | Work history (see below) |
| `notable_projects` | object[] | Notable projects (see below) |
| `education` | object[] | Education entries |
| `professional_development` | string[] | Training and courses |
| `high_value_keywords` | string[] | Keywords for matching |
| `career_narrative` | string | Career story summary |
| `domain_expertise` | string[] | Industry domains |
| `languages` | string[] | Languages spoken |
| `inferred_missing_fields` | string[] | Fields not found in source resume |

### experience[] Fields

| Field | Type | Description |
|-------|------|-------------|
| `employer` | string | Company name |
| `title` | string | Job title |
| `location` | string | Work location |
| `start_year` | integer | Start year |
| `end_year` | integer \| null | End year (null if current) |
| `is_current` | boolean | Currently employed |
| `summary` | string | Role summary |
| `key_contributions` | string[] | Notable achievements |
| `technologies` | string[] | Technologies used |
| `team_size` | integer \| null | Team size managed |
| `seniority_level` | string | Seniority level |
| `keywords` | string[] | Role-specific keywords |

### notable_projects[] Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Project name |
| `description` | string | Project description |
| `role` | string | Candidate's role |
| `start_year` | integer | Start year |
| `end_year` | integer | End year |
| `technologies` | string[] | Technologies used |
| `outcomes` | string[] | Measurable outcomes |
| `keywords` | string[] | Project keywords |

---

# 22. Filename Collision Resolution

Implemented as a utility function in `utils/` (or `services/filename_service.py`) with unit tests.

Algorithm:

1. If `<base>.md` does not exist, use it.
2. Otherwise, try `<base>_a.md`, `<base>_b.md`, … `<base>_z.md`.
3. If all single-letter suffixes are taken, try `<base>_aa.md`, `<base>_ab.md`, … continuing alphabetically.
4. Repeat until an available filename is found.

Properties:

* Suffix applies only on collision.
* Original filename is always preferred.
* Algorithm is deterministic.

---

# 23. Environment Variables

Stored in `.env` at project root (gitignored):

```text
OPENAI_API_KEY=sk-...
```

Loaded at application startup. Never committed to version control.
