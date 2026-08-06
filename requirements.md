# Requirements

**Project:** Job-Hunter

**Version:** 1.7

---

# 1. Project Goal

The goal of this project is to process user-provided job posting URLs and rank them against a candidate's resume and career objectives.

The system uses AI-assisted tools to download, extract, validate, analyze, rank, and save job postings. High-confidence matches may automatically trigger the existing resume customization script.

---

# 2. Project Description

The user supplies a YAML file listing job postings to process (company name and URL). The application downloads each posting, extracts structured information, validates the result, ranks it against the candidate profile, and saves the outcome.

Job search criteria are not manually maintained for ranking. An AI agent analyzes the user's resume information and related input files to generate a structured **job search profile**, which is cached and consumed by the JobHunter Agent for filtering and ranking.

Automatic Internet search, job-board discovery, and company-site crawling are **out of scope**. The user is responsible for finding posting URLs.

### Download Strategy

For each user-provided URL, retrieve the job description using HTTP whenever possible. Fall back to Playwright only when necessary for JavaScript-rendered or dynamic pages.

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

Expected credentials:

* OpenAI API key

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

### job_postings_file

Path to the YAML file listing job postings to process.

Example:

```yaml
job_postings_file: "./config/jobs_to_process.yaml"
```

Each entry contains a user-provided `company` and `url`. See `config/jobs_to_process.yaml.example` for the format.

The path may be overridden per run with `--url-postings <FILE_PATH>`.

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
* `job_search_preferences.file` — path to the user-maintained job search preferences file (`my_job_preferences.yaml`)

Example:

```yaml
search_profile:
  input_files:
    - "C:/path/to/resume.md"
    - "C:/path/to/master_resume_analysis_cache.json"
    - "C:/path/to/LinkedIn_profile.md"              # optional
  output_file: "C:/path/to/job_search_profile.yaml"
  job_search_preferences:
    file: "./config/my_job_preferences.yaml"
```

Typical input files:

| File | Required | Purpose |
|------|----------|---------|
| Resume (Markdown) | Yes | Primary resume content |
| Resume analysis (JSON) | Yes | Structured resume analysis (see `design.md` Section 21) |
| LinkedIn profile (Markdown) | No | Supplementary professional profile |

A production resume sample is available at `test/master_resume.md`. This file contains personal data and shall be excluded from version control. Tests shall use an anonymized copy, similar to `test/master_resume_analysis_cache.json`.

### job_search_profile (generated cache)

The generated cache file is named **`job_search_profile.yaml`** (path configured via `search_profile.output_file`).

This file is produced by an AI agent/LLM and contains structured search criteria derived from the configured input files. It describes what the system **infers from the resume** — not what the user explicitly wants to prioritize.

The JobHunter Agent consumes this profile together with the user-maintained preferences file (see below).

The cache should contain information useful for job searching, such as:

* Probable target job titles
* Equivalent job titles
* Job descriptions and responsibilities
* Skills and technologies
* Seniority level
* Preferred industries (if applicable)
* Excluded job types or titles inferred from resume analysis (if applicable)
* Career direction inferred from resume sources
* Any other information useful for finding matching jobs

The field schema is documented in `design.md` (Section 18).

#### Cache behavior

* During a **full run**, the system shall generate the job search profile **only when the cache file does not exist**. If the cache exists, it is loaded as-is (including any manual edits).
* The `--generate-job-search-profile` flag (see Section 4) **always regenerates** the profile, overwriting any existing cache file.
* Alternatively, the user may delete the cache file manually to force regeneration on the next full run.
* The system shall **not** automatically regenerate the profile based on file timestamps or content changes in v1.

### my_job_preferences.yaml (user-maintained)

The user-maintained preferences file path is configured via `search_profile.job_search_preferences.file`.

Default example location: `config/my_job_preferences.yaml`

This file contains **explicit user preferences** for job searching. It is separate from the AI-generated `job_search_profile.yaml` and shall not be overwritten by the system.

The JobHunter Agent consumes both sources during ranking.

#### AI-generated information (`job_search_profile.yaml`)

* Probable job titles
* Equivalent titles
* Skills
* Industries
* Career direction inferred from resume sources

#### User-provided job search preferences (`my_job_preferences.yaml`)

* Preferred roles (with priority)
* Acceptable roles
* Excluded roles
* Search constraints expressed by the user

User preferences influence:

* **Ranking** — preferred, acceptable, and excluded roles influence semantic scoring
* **Deterministic filtering** — excluded roles are rejected before ranking
* **Ranking** — the LLM considers user preferences when calculating the final confidence score

Example:

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

The field schema is documented in `design.md` (Section 20).

The configured preferences file must exist when the application starts.

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

### models_test and models_prod

OpenAI model identifiers for job search profile generation, ranking, location matching, extraction, and other AI-assisted operations.

The configuration shall define two model sets:

- **`models_test`** — cheaper models used when the CLI is run with `--test`
- **`models_prod`** — models used for normal production runs (without `--test`)

Each set shall include `profile`, `ranking`, `location`, and `extraction` model identifiers. Model selection shall be configurable and not hardcoded.

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
  Job Search Profile        Job Postings File
  (AI cache YAML)          (company + URL list)
  User Preferences                 │
  (my_job_preferences.yaml)        │
         │                         │
         └────────────┬────────────┘
                      │
             Download / Extract / Rank
                      │
               High Confidence?
                      │
               Resume Rework
```

Before the main workflow, a separate profile-generation capability may run to produce or load the cached job search profile (see Section 3.5). User job search preferences are loaded separately from `my_job_preferences.yaml`.

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
5. User job search preferences are loaded from `search_profile.job_search_preferences.file`.
6. Job postings are loaded from `job_postings_file` (or `--url-postings` override).
7. Duplicate postings are removed using the posting history. When a duplicate is found, **date last seen** is updated and further processing for that posting is skipped.
8. Each remaining posting is downloaded (HTTP preferred; Playwright fallback for dynamic pages).
9. Relevant information is extracted, including:

   * Company
   * Job title
   * Description
   * Location
   * Address (when available)
10. Deterministic filtering is applied before ranking:

   * Location filtering
   * Duplicate detection
   * Excluded companies or job types (from job search profile)
   * Excluded roles (from user preferences)
11. Each remaining posting is ranked against the candidate profile using the job search profile, user preferences, and input resume sources. The LLM performs semantic evaluation (resume/job fit, equivalent experience, similar responsibilities, terminology, job title interpretation, alignment with user role preferences) and produces a confidence score between **0.00** and **1.00**.
12. Each posting is written as a Markdown document:

```text
<posting_output>/<company_name>/<job_title>.md
```

13. The posting history is updated.
14. If the confidence score is greater than or equal to **confidence_resume**, the resume customization script is invoked (fire-and-forget).

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

# 7. Language Support

The system shall support job postings in **English** and **French**.

## 7.1 Supported Languages

* **English** (`en`)
* **French** (`fr`)

## 7.2 Extraction

When extracting structured information from a job posting, the system shall:

* Detect the primary language of the posting.
* Preserve all extracted text fields (company, title, location, address, description) in the **original language** of the posting.
* **Not** translate posting content during extraction.

## 7.3 Job Search Profile Generation

When generating the job search profile, the system shall include search criteria suitable for a bilingual job market. Target titles, equivalent titles, and search keywords shall include **both English and French** terms where appropriate (for example, *Software Development Manager* and *Directeur de développement logiciel*).

## 7.4 Search

Search queries shall be built from profile criteria that include bilingual titles and keywords so that postings in either language can be discovered.

## 7.5 Ranking and Location Matching

AI-assisted ranking and location matching shall evaluate postings correctly regardless of whether the posting is in English or French. Equivalent job titles and responsibilities shall be interpreted across languages.

## 7.6 Saved Postings

Downloaded job postings saved as Markdown shall:

* Preserve the original language of the job description and other extracted fields.
* Record the detected language as metadata in the saved file.

---

# 8. Implementation Constraints

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
