# Design

**Project:** Job-Hunter

**Version:** 0.4

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

## Search

* Serper API (Google search provider for v1)

## Browser Automation

* Playwright (fallback when HTTP extraction is insufficient)

## Credentials

* `.env` file at project root (excluded from version control)
* Expected keys: `OPENAI_API_KEY`, `SERPER_API_KEY`

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
        ┌──────────────────┼──────────────────┐
        │                  │                  │
 Search Tools       Processing Tools     Output Tools
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                     Resume Rework
```

The JobHunter Agent is responsible for orchestration.

Business logic shared by multiple tools resides in `services/`. Tool-specific logic resides in `tools/`.

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
│   └── config.yaml               # Production configuration
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
    └── master_resume_analysis_cache.json   # Production sample (gitignored)
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

* Search company websites
* Search job boards
* Search Internet (Serper)
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

Version 1 uses a single primary AI agent.

The JobHunter Agent responsibilities:

* Load configuration.
* Coordinate workflow execution.
* Select and call tools.
* Make AI-assisted decisions when required.
* Generate execution summaries.

Future versions may introduce specialized agents.

### Model Selection

Model identifiers are configuration-driven and not part of the architecture. Initial defaults use cost-effective models for most operations and a more capable model for ranking. Models may be adjusted during testing based on quality, speed, and cost.

| Use case | Model strategy |
|----------|---------------|
| Agent orchestration | Cost-effective model |
| Ranking | More capable model when accuracy is important |
| Location matching | Cost-effective model |
| Extraction (difficult cases) | Configurable per operation |

---

# 8. Tools

## 8.1 Search Tool

Responsible for discovering possible job posting URLs.

A single high-level search tool coordinates separate provider implementations:

| Provider | Strategy |
|----------|----------|
| `SerperSearchProvider` | Google search via Serper API |
| `CompanyWebsiteProvider` | Direct HTTP or browser automation on company career pages |
| `JobBoardProvider` | Site-restricted search queries via Serper (e.g. `site:linkedin.com "Software Development Manager" Montreal`) |

Providers are interchangeable behind a common interface. Future providers (Bing, Brave, MCP services) can be added without changing orchestration.

### Discovery vs. Download

Search tools are responsible for **discovery only** — finding job posting URLs.

Content retrieval is handled separately by the Download Tool (Section 8.3):

1. **Discovery** — Serper (or configured search provider) finds posting URLs.
2. **Download** — HTTP request to the discovered URL (preferred).
3. **Fallback** — Playwright when HTTP is insufficient (JavaScript-rendered or dynamic pages).

## 8.2 Browser Automation Tool

Playwright-based fallback for websites that:

* Require JavaScript execution.
* Dynamically load content.
* Require navigation or interaction.

Implemented behind a dedicated tool interface to allow future replacement (including MCP-based services).

## 8.3 Download Tool

Retrieves job posting content from a discovered URL.

Strategy:

1. HTTP request (preferred)
2. Playwright browser automation (fallback for JavaScript-rendered or dynamic pages)

Input: URL (from search/discovery phase)

Output: Retrieved page content

## 8.4 Extraction Tool

Extracts structured information from a posting.

Expected information:

* Company
* Job title
* Location
* Address
* Description

## 8.5 Ranking Tool

Hybrid approach combining deterministic filtering and LLM-based semantic evaluation.

### Deterministic Filtering (before LLM)

* Location filtering (AI-assisted interpretation of human-readable location definitions)
* Duplicate detection (company + title + location)
* Basic configuration rules

### LLM Semantic Evaluation

* Resume/job fit
* Equivalent experience
* Similar responsibilities
* Company-specific terminology
* Job title interpretation (primary mechanism; optional `title_aliases` in config as supplement)

### Output

```text
confidence = 0.00 – 1.00
```

The final ranking score is generated by the LLM.

## 8.6 History Tool

Maintains processed job posting history.

Responsibilities:

* Duplicate detection (company + title + location)
* History updates (including `date_last_seen` on duplicate encounter)
* Metadata storage

When a duplicate is detected, `date_last_seen` is updated and further processing for that posting is skipped.

## 8.7 Resume Tool

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

## ResumeAnalysis

Loaded from JSON (not YAML).

See Section 18 for the field schema.

## Configuration

Loaded from YAML.

See Section 17 for the proposed schema.

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

```text
Load Configuration

↓

Search (company sites, job boards, Serper)

↓

Filter duplicates (update date_last_seen, skip known postings)

↓

Download

↓

Extract

↓

Deterministic filtering (location, config rules)

↓

LLM ranking

↓

Save posting (with collision-safe filename)

↓

Update history

↓

Run resume customization (fire-and-forget, if confidence ≥ threshold)

↓

Generate summary
```

The workflow shall provide enough runtime information for a user to understand the current operation.

In test mode, processing is limited to two postings and verbose logging is unconditionally enabled.

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

Example:

```text
Loading configuration...
Searching job sources...
Found 25 postings.
Filtering duplicates...
Ranking jobs...
Saving results...
Completed.
```

## Debug

Enabled by:

* Command-line verbose mode.
* Test mode (always enabled, hardcoded).

Provides detailed information for troubleshooting.

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

An anonymized copy of `test/master_resume_analysis_cache.json` shall be created for tests (production sample is gitignored).

### Required Unit Tests

* Filename collision-resolution algorithm (`_a` … `_z`, `_aa`, `_ab`, …)
* Resume script invocation (fire-and-forget, dummy posting)

---

# 14. AI Usage

The LLM shall be used only where deterministic logic is insufficient.

Good AI usage:

* Ranking job postings (semantic evaluation).
* Understanding equivalent job titles.
* Interpreting locations.
* Extracting difficult information.

Avoid AI usage for:

* File operations.
* Configuration loading.
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
resume: "C:\\path\\to\\master_resume.md"
resume_analysis: "C:\\path\\to\\master_resume_analysis_cache.json"

# ── Resume customization script ────────────────────────────────────
resume_rework:
  script_path: "C:\\Users\\ERIC\\Documents\\Code\\job-hunter-resume-rework\\resume_rework.py"
  working_directory: "C:\\Users\\ERIC\\Documents\\Code\\job-hunter-resume-rework"

# ── Thresholds ───────────────────────────────────────────────────
confidence_resume: 0.90

# ── AI models (OpenAI model identifiers) ─────────────────────────
models:
  agent: "gpt-4o-mini"          # Agent orchestration
  ranking: "gpt-4o"             # Semantic ranking (accuracy-critical)
  location: "gpt-4o-mini"       # Location interpretation
  extraction: "gpt-4o-mini"     # Difficult extraction cases

# ── Job search criteria ──────────────────────────────────────────
jobs:
  - title: "Software Development Manager"
    description: "Leadership role managing software development teams"
  - title: "Software Development Team Lead"
    description: "Leadership role managing a team of software developers"
  - title: "Software Quality Assurance Team Lead"
    description: "Leadership role managing a software QA team"

title_aliases:                    # Optional; system does not depend on this list
  - "Software Development Manager"
  - "Engineering Manager"
  - "Software Team Lead"

locations:
  - name: "Montreal Greater Area"
    description: "Montreal and surrounding areas accessible by public transport or reasonable commute"
  - name: "South Shore"
    description: "Longueuil, Brossard, Saint-Hubert, and nearby cities"

# ── Search sources ───────────────────────────────────────────────
web_sites:
  companies:
    - url: "https://jobsearch.alstom.com/"
    - url: "https://www.desjardins.com/qc/fr/carriere.html"
    - url: "https://www.adacel.com/careers"
    - url: "https://emploi.hydroquebec.com/"
  job_boards:
    - name: "LinkedIn"
    - name: "Indeed"
    - name: "Workday"
    - name: "Greenhouse"
    - name: "BambooHR"
    - name: "Eightfold"
    - name: "UltiPro"

# ── Search provider ──────────────────────────────────────────────
search:
  provider: serper                # v1: Serper (Google); future: bing, brave, mcp
```

### CLI Override

```text
uv run job-hunter --config .test/config.yaml
uv run job-hunter --test
```

| Flag | Effect |
|------|--------|
| `--config PATH` | Configuration file path (default: `config/config.yaml`) |
| `--test` | Limit to 2 postings; enable verbose (hardcoded) |
| `--verbose` | Enable debug logging (ignored when `--test` is active, since test mode always enables verbose) |

---

# 18. Resume Analysis JSON Schema

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

# 19. Filename Collision Resolution

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

# 20. Environment Variables

Stored in `.env` at project root (gitignored):

```text
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...
```

Loaded at application startup. Never committed to version control.
