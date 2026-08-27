# Job-Hunter

Job-Hunter is an AI-assisted Python application that searches the Internet for job postings that best match a candidate's resume and career objectives.

The project discovers job postings from multiple sources, ranks them according to the candidate's profile, saves the results locally, and can automatically invoke a resume customization script for high-confidence matches.

## Documentation

The project documentation is organized as follows:

* **requirements.md** — Functional requirements and project objectives. This document is the authoritative source for *what* the software must do.
* **design.md** — Software architecture, design decisions, implementation strategy, and technical details. This document is the authoritative source for *how* the software is implemented.

## Status

Project currently **on hold** for the foreseeable future.
See branch `job_search_experiment` for the latest dev.

This project was "phase-2" of the project [job-hunter-resume-rework](https://github.com/IntoCpp/job-hunter-resume-rework), where I completed the "resume rework" part. This was to try/test the "search web for relevant jobs" part and fuse it later. But as noted in `job_search_experiment` branch "Competing with specialized job search platforms (such as LinkedIn) is well beyond the scope of this personal project."

## Work plan

* Phase 1 — Understanding:
  * Read the project documentation and ask any questions before implementation.
  * Make sure the files under "./cursor/rules" are formatted to be used efficiently by Cursor. The current format is Markdown, you can change it to something more efficient for you. Do not change, add or remove any rules.
* Phase 2 — Setup
  * Create the `.gitigore` file for this project. Keep it updated as needed in this step.
  * Setup the Python project:

```text
uv
dependencies
project structure
initial tests
```  

* Phase 3 — Implementation
  * Implement the project according to requirements.md and design.md.

### Implementation with Cursor

Phase 3 will be done as a conversation plan like this:

1. Project skeleton + configuration loading.
2. Models + history storage.
3. Search tools.
4. Extraction.
5. Ranking.
6. Resume integration.
7. Improvements.
