# Requirements

**Project:** Job-Hunter

**Version:** 1.0

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

The discovered postings are analyzed and ranked according to how well they match the candidate's resume and search criteria.

The system shall support Internet search engines (Google, Bing, Brave, etc.) to discover job postings beyond the configured company and job-board URLs.

The system shall be designed so that search tools (company websites, search engines, job boards, browser automation, or future MCP-backed services) are interchangeable without requiring changes to the JobHunter Agent orchestration logic.

---

# 3. Configuration

The project uses a YAML configuration file containing all user-configurable information.

The detailed YAML schema is outside the scope of this document and will be documented separately.

## 3.1 Output

### posting_output

Folder where job postings and generated files are saved.

Example:

```yaml
posting_output: "C:\Users\ERIC\Documents\job_hunter_finds\"
```

Future documentation shall describe the generated files, directory structure, and naming conventions.

### Logging output

The system shall:

* Display execution progress on standard output.
* Generate a log file for each execution.
* Store log files in the configured output folder.
* Include sufficient information to understand the execution flow and diagnose failures.

Example:

posting_output/
└── logs/
    ├── 2026-07-27_143100.log

---

## 3.2 Input / Output

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
* Date last seen (future enhancement)
* Ranking score
* Path to the Markdown description
* Additional metadata (when reasonably small)

Large fields such as the complete job description shall be stored separately.

Duplicate detection shall use:

* Company
* Job title
* Location

rather than the posting URL alone.

---

## 3.3 Input

### Resume

Path to the resume in Markdown format.

### resume_analysis

Path to the YAML file containing the structured analysis of the resume.

### list_of_jobs

List of desired job types.

Each job definition contains:

* title
* description

The title is only a guideline.

The search agent shall also recognize equivalent or similar titles that describe the same type of position.

The description exists to clarify ambiguous titles.

Example:

* Software Development Manager
* Software Team Lead
* Software Engineering Manager
* Software Quality Assurance Manager

---

### list_of_locations

List of acceptable locations.

A location may be expressed as:

* City
* Region
* Postal code
* Geographic area

Any posting outside the acceptable locations shall be rejected.

The exact representation will be determined later.

---

### list_of_web_sites

List of preferred search sources.

This list may include:

#### Preferred companies

Examples:

* https://jobsearch.alstom.com/
* https://www.desjardins.com/qc/fr/carriere.html
* https://www.adacel.com/careers
* https://emploi.hydroquebec.com/

#### Job boards

Examples:

* LinkedIn
* Indeed
* Workday
* Greenhouse
* BambooHR
* Eightfold
* UltiPro

Additional sources may be added without changing the project architecture.

---

### confidence_resume

Confidence threshold (0.00–1.00).

When a posting reaches or exceeds this threshold, the system shall automatically invoke the resume customization script.

---

# 4. Command Line Options

## test_mode

Limits processing to a small number of postings.

Purpose:

* Faster development
* Lower AI costs
* Easier debugging

---

## verbose

Produces detailed execution information.

Verbose mode shall automatically be enabled while test mode is active.

---

# 5. High-Level Architecture

```
                JobHunter Agent
                      │
      ┌───────────────┼────────────────┐
      │               │                │
 Search Tool     Company Tool     Job Board Tool
      │               │                │
      └───────────────┼────────────────┘
                      │
             Job Description
                      │
                Ranking Tool
                      │
               High Confidence?
                      │
               Resume Rework
```

## Architecture Philosophy

* Each capability shall be implemented as an independent tool with a clean interface.
* Tools shall be designed for future interchangeability.
* A tool may internally use AI agents and additional tools.
* Future implementations may replace local tools with MCP-backed services without requiring architectural changes.

---

# 6. Workflow

1. The JobHunter Agent starts execution.
2. Command-line options are processed.
3. The YAML configuration file is loaded.
4. Search tools discover job posting URLs from:

   * Company websites
   * Job boards
   * Internet search engines
5. Duplicate postings are removed using the posting history.
6. Each remaining posting is downloaded.
7. Relevant information is extracted, including:

   * Company
   * Job title
   * Description
   * Location
   * Address (when available)
8. Each posting is ranked against the candidate profile using a confidence score between **0.00** and **1.00**.
9. Each posting is written as a Markdown document:

```
<posting_output>/<business_name>/<job_title>.md
```

If necessary, a unique suffix shall be added.

Examples:

```
Software_Development_Manager.md
Software_Development_Manager_a.md
Software_Development_Manager_b.md
```

10. The posting history is updated.
11. If the confidence score is greater than or equal to **confidence_resume**, the resume customization script is automatically executed.

---

# 7. Implementation Constraints

The initial implementation shall use:

* Python
* OpenAI Agents SDK
* `uv` for package and virtual environment management
* `uv run` to execute the application
* Cursor as the AI-assisted development environment
* Visual Studio Code as the primary code editor
* Windows as the primary execution platform

Docker, MCP services, and additional infrastructure are considered future enhancements and shall not be required for the first working version.
