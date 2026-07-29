# Job-Hunter

Job-Hunter is an AI-assisted Python application that searches the Internet for job postings that best match a candidate's resume and career objectives.

The project discovers job postings from multiple sources, ranks them according to the candidate's profile, saves the results locally, and can automatically invoke a resume customization script for high-confidence matches.

## Documentation

The project documentation is organized as follows:

* **requirements.md** — Functional requirements and project objectives. This document is the authoritative source for *what* the software must do.
* **design.md** — Software architecture, design decisions, implementation strategy, and technical details. This document is the authoritative source for *how* the software is implemented.

## quick start

### Run the tool

First we recommend generating your job profile based you resume (and other file). Indicate where to find them in the [config.yaml](./config/config.yaml) file in section `search_profile`. This will generate your profile and save it. **Make sure to review it**, it will be used each run until you delete it. A new one is generated if not found, so if you change your resume (or other files), just delete your generated profile.

> uv run job-hunter --generate-job-search-profile --config config/config.yaml

Or change the prod [config.yaml](./config/config.yaml) and just run 

> uv run job-hunter --generate-job-search-profile --config config/config.yaml

### Run uinot tests

> uv run pytest -v


## Status

Project currently in the design phase.

## Work plan

* Phase 1 — Understanding: DONE
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
