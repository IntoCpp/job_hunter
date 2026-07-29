# Requirements

**Project:** Job-Hunter

**Version:** 1.4

---

# 1. Project Goal

The goal of this project is to scan the Internet for job postings that best match a candidate's resume and career objectives.

The system uses AI agents and specialized tools to discover, analyze, rank, and save job postings. High-confidence matches may automatically trigger the existing resume customization script.

---

# 2. Project Description

The project uses AI agents and tools to search multiple sources for job postings, including:

* Company career websites
* Job boards
* Internet search engines
* Future search sources

The discovered postings are analyzed and ranked according to how well they match the candidate's profile.

Job search criteria are not manually maintained. An AI agent analyzes the user's resume information and related input files to generate a structured **job search profile**, which is cached and consumed by the JobHunter Agent for discovery, filtering, and ranking.

For version 1, Internet search shall use **Serper** as the Google search provider. The search provider must be implemented behind an abstraction so it can be replaced later by another API, MCP service, or provider.

The system shall be designed so that search tools (company websites, search engines, job boards, browser automation, or future MCP-backed services) are interchangeable without requiring changes to the JobHunter Agent orchestration logic.

Search shall use a single high-level search tool with separate provider implementations for company websites, job boards, and search engines.

### Job Discovery and Download Strategy

For version 1, job posting discovery and content retrieval follow a two-phase approach:

1. **Discovery** — Use Serper (or another configured search provider) to find job posting URLs. For job boards, use site-restricted search queries (e.g. `site:linkedin.com "Software Development Manager" Montreal`).
2. **Download** — Once a URL is discovered, retrieve the job description directly using HTTP whenever possible. Fall back to Playwright only when necessary for JavaScript-rendered or dynamic pages.

---

# 3. Configuration

The project uses a YAML configuration file containing all user-configurable information.

## 3.1 Configuration File Location

* **Production:** `config/config.yaml`
* **Testing:** `.test/config.yaml` (used by tests and local development to avoid modifying production configuration)

The application shall support a command-line option to override the configuration file path (default: `config/config.yaml`).

The YAML configuration schema is documented in `design.md` (Section 17).

## 3.2 Credentials

API keys and secrets shall be stored in a `.env` file at the project root.

The `.env` file shall be excluded from version control.

Expected credentials for version 1:

* OpenAI API key (OpenAI Agents SDK)
* Serper API key

## 3.3 Output

### posting_output

Folder where job postings and generated files are saved.

Example:

```yaml
posting_output: "C:/Users/ERIC/Documents/job_hunter_finds/"
```

Saved posting structure:

```text
<posting_output>/<company_name>/<job_title>.md
```

Company and job title names shall be sanitized for use as filesystem paths (invalid characters removed or replaced, spaces converted to underscores).

If a target filename already exists, an alphabetical suffix shall be appended using the collision-resolution algorithm described in Section 6.9.

### Logging output

The system shall:

* Display execution progress on standard output.
* Generate a log file for each execution.
* Store log files in the configured output folder.
* Include sufficient information to understand the execution flow and diagnose failures.

Example:

```text
posting_output/
└── logs/
    └── 2026-07-27_143100.log
```

---

## 3.4 Input / Output

### posting_history

Path to the history file containing every previously processed posting.

Example:

```yaml
posting_history: "C:\Users\ERIC\Documents\job_hunter_finds\posting_history.yaml"
```

The history file shall be updated after every execution.

The history shall contain, whenever available:

* Company
* Job title
* Location
* URL
* Date first found
* Date last seen
* Ranking score
* Path to the Markdown description
* Additional metadata (when reasonably small)

When a duplicate posting is detected (same company, job title, and location), the system shall update **date last seen** to indicate the posting was encountered again.

Large fields such as the complete job description shall be stored separately.

Duplicate detection shall use:

* Company
* Job title
* Location

rather than the posting URL alone.

---

## 3.5 Input

### search_profile

Configuration for generating the AI-derived job search profile.

The configuration defines:

* `input_files` — list of file paths sent to the AI agent/LLM when generating the profile
* `output_file` — path and filename of the generated cache file

Example:

```yaml
search_profile:
  input_files:
    - "C:/path/to/resume.md"
    - "C:/path/to/master_resume_analysis_cache.json"
    - "C:/path/to/LinkedIn_profile.md"              # optional
    - "C:/path/to/additional_profile_information.yaml"  # optional
  output_file: "C:/path/to/job_search_profile.yaml"
```

Typical input files:

| File | Required | Purpose |
|------|----------|---------|
| Resume (Markdown) | Yes | Primary resume content |
| Resume analysis (JSON) | Yes | Structured resume analysis (see `design.md` Section 19) |
| LinkedIn profile (Markdown) | No | Supplementary professional profile |
| Additional profile information (YAML) | No | Manual preferences (e.g. excluded companies, additional locations) |

A production resume sample is available at `test/master_resume.md`. This file contains personal data and shall be excluded from version control. Tests shall use an anonymized copy, similar to `test/master_resume_analysis_cache.json`.

The exact schema for `additional_profile_information.yaml` may be defined later.

### job_search_profile (generated cache)

The generated cache file is named **`job_search_profile.yaml`** (path configured via `search_profile.output_file`).

This file is produced by an AI agent/LLM and contains structured search criteria derived from the configured input files. The JobHunter Agent consumes this profile instead of a manually maintained list of job titles.

The cache should contain information useful for job searching, such as:

* Target job titles
* Equivalent job titles
* Job descriptions and responsibilities
* Skills and technologies
* Seniority level
* Preferred industries (if applicable)
* Excluded job types or titles (if applicable)
* Any other information useful for finding matching jobs

The field schema is documented in `design.md` (Section 18).

#### Cache behavior

* During a **full run**, the system shall generate the job search profile **only when the cache file does not exist**. If the cache exists, it is loaded as-is (including any manual edits).
* The `--generate-job-search-profile` flag (see Section 4) **always regenerates** the profile, overwriting any existing cache file.
* Alternatively, the user may delete the cache file manually to force regeneration on the next full run.
* The system shall **not** automatically regenerate the profile based on file timestamps or content changes in v1.

### locations

List of acceptable locations.

Each location entry contains:

* `name` — short human-readable label
* `guidance` — clarifies the geographic scope for AI-assisted location matching

Location matching shall be performed using AI-assisted interpretation.

The design shall allow future migration to structured geographic data (postal codes, coordinates) without changing the overall architecture.

Example:

```yaml
locations:
  - name: "Montreal Greater Area"
    guidance: "Montreal and surrounding areas accessible by public transport or reasonable commute"

  - name: "South Shore"
    guidance: "Longueuil, Brossard, Saint-Hubert, and nearby cities"
```

Any posting outside the acceptable locations shall be rejected.

### web_sites

List of preferred search sources, including company career pages and job boards.

Additional sources may be added without changing the project architecture.

#### Preferred companies

Examples:

* https://jobsearch.alstom.com/
* https://www.desjardins.com/qc/fr/carriere.html
* https://www.adacel.com/careers
* https://emploi.hydroquebec.com/

#### Job boards

Job boards are used as discovery sources. Posting URLs are found via site-restricted search queries through the configured search provider (Serper for v1). Content is downloaded directly from the discovered URL (HTTP first, Playwright fallback).

Examples:

* LinkedIn
* Indeed
* Workday
* Greenhouse
* BambooHR
* Eightfold
* UltiPro

### models

OpenAI model identifiers for agent orchestration, job search profile generation, ranking, and other AI-assisted operations.

Model selection shall be configurable and not hardcoded. The initial implementation shall use cost-effective models for most operations and allow more capable models for complex ranking or ambiguous cases.

### confidence_resume

Confidence threshold (0.00–1.00). Default: **0.90**.

When a posting reaches or exceeds this threshold, the system shall automatically invoke the resume customization script. Postings below the threshold remain in the history file and can be processed manually with the resume customization script if desired.

---

## 3.6 Resume Customization Script

The resume customization script is a **separate project** and shall not be modified by Job-Hunter.

| Setting | Value |
|---------|-------|
| Script path | `C:\Users\ERIC\Documents\Code\job-hunter-resume-rework\resume_rework.py` |
| Working directory | `C:\Users\ERIC\Documents\Code\job-hunter-resume-rework\` |

The script must be invoked from its own working directory because it uses relative paths for configuration and input files.

Invocation example:

```text
uv run resume_rework.py --job-posting C:\Users\ERIC\Documents\job_hunter_finds\Alstom\Senior_software_developper.md
```

Only the `--job-posting` argument is required. Job-Hunter shall pass the path to the saved Markdown posting file.

When triggered, the script creates output files in the same folder as the job posting:

* `<name>_analysis_cache.json`
* `<name>_cresume.md`
* `<name>_cresume.docx`
* `<name>_changes_made.txt`
* `<name>_cover_letter.txt`

Invocation shall be **fire-and-forget**: Job-Hunter shall not wait for the script to complete. A unit test shall verify invocation using a dummy job posting in the test folder.

---

# 4. Command Line Options

## test_mode

Enabled via the `--test` command-line flag. Not enabled by default.

Limits processing to **two postings**.

Purpose:

* Faster development
* Lower AI costs
* Easier debugging

## verbose

Enabled via the `--verbose` command-line flag.

Produces detailed execution information.

When `--test` is present, verbose is **automatically and unconditionally enabled** as well. This coupling is hardcoded and cannot be disabled via CLI.

## generate_job_search_profile

Enabled via the `--generate-job-search-profile` command-line flag. Not enabled by default.

Runs **only** the job search profile generation step and then exits. No web search, download, extraction, ranking, history update, or resume customization is performed.

Purpose:

* Generate or regenerate `job_search_profile.yaml` for user review before a full run.
* Allow the user to revise the generated profile manually before searching for jobs.

Behavior:

* Loads configuration.
* Regenerates the job search profile via the AI agent, **overwriting** any existing cache file.
* Writes the result to `search_profile.output_file`.
* Exits.

The user may edit the generated file before launching a full run. During a full run, the existing cache is loaded without regeneration (unless the cache file is missing).

---

# 5. High-Level Architecture

```text
                JobHunter Agent
                      │
         ┌────────────┴────────────┐
         │                         │
  Job Search Profile        Search Tools
    (cached YAML)          (company / board / Serper)
         │                         │
         └────────────┬────────────┘
                      │
             Job Description
                      │
                Ranking Tool
                      │
               High Confidence?
                      │
               Resume Rework
```

Before the main workflow, a separate profile-generation capability may run to produce or load the cached job search profile (see Section 3.5).

## Architecture Philosophy

* Each capability shall be implemented as an independent tool with a clean interface.
* Tools shall be designed for future interchangeability.
* A tool may internally use AI agents and additional tools.
* Future implementations may replace local tools with MCP-backed services without requiring architectural changes.
* Reusable business logic shared by multiple tools shall reside in `services/` (see `design.md`).

---

# 6. Workflow

## 6.1 Full Run

1. The JobHunter Agent starts execution.
2. Command-line options are processed. If `--generate-job-search-profile` is present, follow Section 6.2 instead.
3. The YAML configuration file is loaded.
4. The job search profile is loaded from cache, or generated if the cache file does not exist (see Section 3.5).
5. Search tools discover job posting URLs using criteria from the job search profile:

   * Company websites
   * Job boards
   * Internet search engines (via Serper)
6. Duplicate postings are removed using the posting history. When a duplicate is found, **date last seen** is updated and further processing for that posting is skipped.
7. Each remaining posting is downloaded (HTTP preferred; Playwright fallback for dynamic pages).
8. Relevant information is extracted, including:

   * Company
   * Job title
   * Description
   * Location
   * Address (when available)
9. Deterministic filtering is applied before ranking:

   * Location filtering
   * Duplicate detection
   * Excluded companies or job types (from job search profile or additional profile information)
10. Each remaining posting is ranked against the candidate profile using the job search profile and input resume sources. The LLM performs semantic evaluation (resume/job fit, equivalent experience, similar responsibilities, terminology, job title interpretation) and produces a confidence score between **0.00** and **1.00**.
11. Each posting is written as a Markdown document:

```text
<posting_output>/<company_name>/<job_title>.md
```

12. The posting history is updated.
13. If the confidence score is greater than or equal to **confidence_resume**, the resume customization script is invoked (fire-and-forget).

## 6.2 Profile-Only Run (`--generate-job-search-profile`)

1. Command-line options are processed.
2. The YAML configuration file is loaded.
3. The job search profile is **regenerated** via the AI agent (existing cache is overwritten).
4. The result is written to `search_profile.output_file`.
5. Execution stops. No further steps are performed.

## 6.9 Filename Collision Resolution

When a target filename already exists, append an alphabetical suffix: `_a`, `_b`, … `_z`, then `_aa`, `_ab`, etc., until an available filename is found.

* The suffix applies only when a collision occurs.
* The original filename is always preferred.
* The algorithm must be deterministic.

Examples:

```text
Software_Development_Manager.md
Software_Development_Manager_a.md
Software_Development_Manager_b.md
...
Software_Development_Manager_z.md
Software_Development_Manager_aa.md
Software_Development_Manager_ab.md
```

---

# 7. Implementation Constraints

The initial implementation shall use:

* Python
* OpenAI Agents SDK
* Serper (Google search provider)
* Playwright (browser automation fallback)
* `uv` for package and virtual environment management
* `uv run` to execute the application
* Cursor as the AI-assisted development environment
* Visual Studio Code as the primary code editor
* Windows as the primary execution platform

Browser automation is a fallback mechanism when HTTP extraction is insufficient.

Docker, MCP services, and additional infrastructure are considered future enhancements and shall not be required for the first working version.
