# Job-Hunter

Job-Hunter is an AI-assisted Python application that processes user-provided job posting URLs, ranks them against a candidate profile, saves the results locally, and can automatically invoke a resume customization script for high-confidence matches.

## Documentation

* **requirements.md** — Functional requirements and project objectives.
* **design.md** — Software architecture and technical design.
* **change-request.md** — Approved change requests and implementation decisions.

## Quick start

### 1. Configure

Copy `config/config.yaml.example` to `config/config.yaml` and adjust paths.

Set `job_postings_file` to your list of postings (see `config/jobs_to_process.yaml.example`):

```yaml
job_postings_file: "./config/jobs_to_process.yaml"
```

### 2. Generate job search profile (first time)

```bash
uv run job-hunter --generate-job-search-profile --config config/config.yaml
```

Review the generated profile before running a full workflow.

### 3. Process postings

```bash
uv run job-hunter --config config/config.yaml
```

Useful options:

```bash
uv run job-hunter --test --skip-resume --config config/config.yaml
uv run job-hunter --max 5 --config config/config.yaml
uv run job-hunter --url-postings ./my_jobs.yaml --config config/config.yaml
```

### Run unit tests

```bash
uv run pytest -v
```

## Status

Active development. Automated job search was removed in favor of user-provided URL lists.

## Change History

- **2026-08-04** — Removed automated job search (Serper, job boards, company crawling). Added `job_postings_file` input and `--url-postings` CLI option. User-provided company names are authoritative. See branch [job_search_experiment](https://github.com/IntoCpp/job_hunter/tree/job_search_experiment) for the code with web-search feature, the README contains a comment specific to the branch.
- **2026-07-30** — Added pipeline validation, split history files, artifact saving, externalized prompts, improved ranking output, `--skip-resume`, and `--max N`.
- **2026-07-29** — Enabled OpenAI Responses API logging and fixed company page link normalization.
- **2026-07-28** — Initial end-to-end implementation.
