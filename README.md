# Job-Hunter

Job-Hunter is an AI-assisted Python application that processes user-provided job posting URLs, ranks them against a candidate profile, saves the results locally, and can automatically invoke a resume customization script for high-confidence matches.

## Documentation

* **requirements.md** — Functional requirements and project objectives.
* **design.md** — Software architecture and technical design.
* **change-request.md** — Approved change requests and implementation decisions. Instead of pasting a long prompt I use this file. It serve as a draft that I review and then simply ask my AI to execute the changes in here.

## Quick start

### 1. Configure

Copy `config/config.yaml.example` to `config/config.yaml` and adjust paths.

Define both `models_test` (cheaper models for `--test` runs) and `models_prod` (production models). The CLI selects the appropriate set automatically.

Set `job_postings_file` to your list of postings (see `config/jobs_to_process.yaml.example`):

```yaml
job_postings_file: "./config/jobs_to_process.yaml"
```

### 2. Generate job search profile (first time)

The app will give you a ranking and some positive/negative aspect of the posting for you. This is based on a job profile you are looking for. To help out, you can create the first profile using the `--generate-job-search-profile` option. It will generate a profile file based on the input documents (resume, ...). Just edit the file to fit what you want, add special aspect of a job you wish for or add a second job type that you are interested in. You can have more than one job profile in it. For example, your resume and profile is for a store manager, you can add a profile as sales director; to increase ranking of those jobs.

```bash
uv run job-hunter --generate-job-search-profile --config config/config.yaml
```

Review the generated profile before running a full workflow. Edit for the job(s) you wish to apply for.

### 3. Process postings

#### Start the debug browser

Job-Hunter retrieves postings in three steps: HTTP, then headless Playwright, then a **browser session** that connects to your own Edge window. The first two methods often fail on sites that use CAPTCHA, bot detection, or login walls (for example Eaton/eightfold.ai). The browser session step reuses a real browser profile so those pages can load the same way they do when you browse manually.

That third step does **not** launch Edge for you. It connects to an Edge instance you have already started with remote debugging enabled on port **9222** (configurable via `browser_session.debug_port` in `config.yaml`).

**Why a separate Edge instance is required**

- The `--remote-debugging-port` flag only takes effect when a **new** Edge process starts. It cannot be enabled on Edge that is already running.
- If you click a normal Edge shortcut while Edge is open, Windows usually opens another window in the **existing** process, which ignores the debug flag. Job-Hunter then fails with `ECONNREFUSED` on port 9222.
- A **separate profile** (`--user-data-dir`) forces a new Edge process without closing your everyday Edge windows. You can keep all your usual tabs open; use this debug Edge only for job URLs Job-Hunter should fetch.

**Do not use a Windows shortcut** for this — shortcuts often drop or mis-parse the flags. Use the provided batch file instead:

```text
start-edge-debug.bat
```

This opens a dedicated Edge window (first launch may ask setup questions). Leave it open for the whole Job-Hunter run. Open job posting URLs in **that** window (sign in once if needed; cookies are stored in `%USERPROFILE%\EdgeDebugProfile`).

Optional check before running Job-Hunter:

```powershell
Invoke-WebRequest http://127.0.0.1:9222/json/version
```

A JSON response with browser version information means the debug port is ready.

Job-Hunter will prompt you to confirm the browser is ready before processing postings.

```bash
uv run job-hunter --config config/config.yaml
```

Useful options:

```bash
uv run job-hunter --test --skip-resume --config config/config.yaml   # uses models_test
uv run job-hunter --max 5 --config config/config.yaml                # uses models_prod
uv run job-hunter --url-postings ./my_jobs.yaml --config config/config.yaml
```

### Run unit tests

```bash
uv run pytest -v
```

## Status

Active development. Automated job search was removed in favor of user-provided URL lists.

## Change History

- **2026-08-07** — Added `start-edge-debug.bat` and README guidance for launching a dedicated debug Edge instance (required for browser-session retrieval when HTTP/Playwright fail).
- **2026-08-06** — Browser session fallback now connects to a running Edge/Chrome instance via CDP (`debug_port` 9222 by default) instead of launching the live profile. CLI prompts for debug browser confirmation before processing. Optional dedicated-profile fallback requires explicit `user_data_dir`.
- **2026-08-06** — Added multi-step retrieval fallback (HTTP → Playwright → browser session). Validation failures trigger the next method. Retrieval method is recorded in history and artifacts; failed downloads include company and retrieval attempts. Optional `browser_session` config (Edge/Chrome). CLI prints a warning summary when retrievals fail.
- **2026-08-06** — Replaced single `models` config section with `models_test` and `models_prod`. The CLI `--test` flag now selects `models_test` automatically; production runs use `models_prod`.
- **2026-08-04** — Removed automated job search (Serper, job boards, company crawling). Added `job_postings_file` input and `--url-postings` CLI option. User-provided company names are authoritative. See branch [job_search_experiment](https://github.com/IntoCpp/job_hunter/tree/job_search_experiment) for the code with web-search feature, the README contains a comment specific to the branch.
- **2026-07-30** — Added pipeline validation, split history files, artifact saving, externalized prompts, improved ranking output, `--skip-resume`, and `--max N`.
- **2026-07-29** — Enabled OpenAI Responses API logging and fixed company page link normalization.
- **2026-07-28** — Initial end-to-end implementation.
