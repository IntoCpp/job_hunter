# Design

**Project:** Job-Hunter

**Version:** 0.2 (Draft)

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

Business logic should reside inside tools whenever practical.

---

# 5. Project Structure

Initial proposal:

```text
job-hunter/

├── README.md
├── requirements.md
├── design.md
├── pyproject.toml
├── config/
│   └── config.yaml
│
├── src/
│   └── job_hunter/
│       ├── agent/
│       ├── tools/
│       ├── models/
│       ├── services/
│       └── utils/
│
├── tests/
│
└── sample_data/
```

Folder responsibilities:

* **agent** — orchestration logic
* **tools** — AI and non-AI capabilities
* **services** — reusable business logic
* **models** — internal data structures
* **utils** — generic helper functions

---

# 6. Architectural Philosophy

The project follows a tool-oriented architecture.

Each capability shall exist as an independent module with a clearly defined interface.

Examples:

* Search company websites
* Search job boards
* Search Internet
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

---

# 8. Tools

## 8.1 Search Tool

Responsible for discovering possible job postings.

Possible implementations:

* Search engines
* Company websites
* Job boards
* Browser automation

The search tool should support multiple strategies.

A simple HTTP request should be preferred when sufficient.

Browser automation may be used when required for websites that:

* Require JavaScript execution.
* Dynamically load content.
* Require navigation or interaction.

---

## 8.2 Download Tool

Retrieves job posting content.

Possible implementations:

* HTTP requests
* Browser automation

Input:

* URL

Output:

* Retrieved page content

---

## 8.3 Extraction Tool

Extracts structured information from a posting.

Expected information:

* Company
* Job title
* Location
* Address
* Description

---

## 8.4 Ranking Tool

Compares:

* Resume information
* Job posting information

Produces:

```text
confidence = 0.00 – 1.00
```

---

## 8.5 History Tool

Maintains processed job posting history.

Responsibilities:

* Duplicate detection
* History updates
* Metadata storage

---

## 8.6 Resume Tool

Invokes the existing resume customization script.

---

# 9. Internal Models

Expected logical models:

## JobPosting

Contains:

* Title
* Company
* Location
* URL
* Markdown filename
* Confidence score
* Description

---

## ResumeAnalysis

Loaded from YAML.

Contains structured resume information.

---

## Configuration

Loaded from YAML.

Contains user-defined options.

---

# 10. Workflow

```text
Load Configuration

↓

Search

↓

Download

↓

Extract

↓

Remove duplicates

↓

Rank

↓

Save posting

↓

Update history

↓

Run resume customization (optional)

↓

Generate summary
```

The workflow shall provide enough runtime information for a user to understand the current operation.

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

---

## Debug

Enabled by:

* Command-line verbose mode.
* Test mode.

Provides detailed information for troubleshooting.

Debug logging may include:

* Function execution details.
* Input parameters when useful.
* Operation results.
* External calls.
* Intermediate processing information.
* Additional diagnostic information.

---

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

Log output shall contain timestamp with date.

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

---

# 14. AI Usage

The LLM shall be used only where deterministic logic is insufficient.

Good AI usage:

* Ranking job postings.
* Understanding equivalent job titles.
* Interpreting locations.
* Extracting difficult information.

Avoid AI usage for:

* File operations.
* Configuration loading.
* Duplicate detection.
* Sorting.
* Simple data transformations.

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
