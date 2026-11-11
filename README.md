# Evaluate AI Applications

OpenAI Academy · standalone guided lab

This bundle contains the guided exercise, its required data, and the existing reference material. You do not need to clone a repository or obtain another course bundle.

**Verification:** The original guided workflows received bounded live checks on macOS. This security update is checked separately with offline compatibility and security tests; it has not received a new paid end-to-end run. See [results and known limitations](KNOWN-ISSUES.md), including operating systems not runtime-tested. The standard MIT license is included at the packaging requester’s direction.

## 1. Download and extract

Download `evaluate-ai-applications-guided-lab.zip`. Extract it using your file manager, then open a terminal in the extracted `evaluate-ai-applications-guided-lab` directory. That directory contains this README, `requirements.txt`, and `labs/` and is called the **bundle root** throughout the instructions. Do not run commands inside the ZIP or from the inner lab folder.

From the folder containing the downloaded ZIP, macOS/Linux:

```bash
unzip evaluate-ai-applications-guided-lab.zip
cd evaluate-ai-applications-guided-lab
```

Windows PowerShell:

```powershell
Expand-Archive -LiteralPath .\evaluate-ai-applications-guided-lab.zip -DestinationPath .
Set-Location .\evaluate-ai-applications-guided-lab
```

## 2. Prerequisites and installation

- Python **3.12 or 3.13**. The original guides said 3.10+, but the source manifest requires 3.12+. Use the documented versions for this bundle.
- Node.js **24 LTS**, including npm. Promptfoo remains **0.121.18**; `package-lock.json` fixes the dependency versions used by this bundle.
- A text editor and browser. The macOS/Linux preview commands use `jq`; install it with your OS package manager, or use the Python JSON preview below. PowerShell examples do not require jq.
- Internet access to install dependencies, plus an OpenAI API project with billing, a project-scoped API key, and access to the models listed below. ChatGPT subscriptions do not configure this API key or project.

Create a new virtual environment in this bundle; do not reuse another lab's environment.

macOS/Linux:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export PROMPTFOO_PYTHON="$PWD/.venv/bin/python"
export PROMPTFOO_CONFIG_DIR="$PWD/.promptfoo"
node --version
npm ci --ignore-scripts --registry=https://registry.npmjs.org
node scripts/promptfoo.mjs --version
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:PROMPTFOO_PYTHON = (Join-Path (Get-Location) '.venv\Scripts\python.exe')
$env:PROMPTFOO_CONFIG_DIR = (Join-Path (Get-Location) '.promptfoo')
node --version
npm ci --ignore-scripts --registry=https://registry.npmjs.org
node scripts/promptfoo.mjs --version
```

If you installed Python 3.13 on Windows, use `py -3.13` for the first command. If PowerShell blocks virtual-environment activation, invoke `.\.venv\Scripts\python.exe` wherever the guide says `python` and keep the `PROMPTFOO_PYTHON` setting above; no execution-policy change is required. Where PowerShell blocks `npm.ps1`, use `npm.cmd ci --ignore-scripts --registry=https://registry.npmjs.org`.

`requirements.txt` pins the direct dependencies and applies `constraints.txt`. Security fixes update supporting libraries while preserving the course’s OpenAI SDK versions. `npm ci --ignore-scripts --registry=https://registry.npmjs.org` installs the exact Node dependency tree and verifies its package integrity hashes. Install scripts are disabled; optional local-model integrations outside this lab are not configured. No global Promptfoo installation is needed. Run Promptfoo through `node scripts/promptfoo.mjs` as shown in the guide; it uses only this bundle’s installation.

The viewer binds only to `127.0.0.1` and rejects requests from unrelated websites. Open the localhost URL it prints and stop it with Ctrl+C. Do not launch a separate bare `promptfoo view` command or expose the viewer on a network. If port 15500 is occupied, set `API_PORT` to another unused port before starting the viewer.

Promptfoo is a third-party tool with usage telemetry. The bundle launcher disables normal telemetry and update checks; this Promptfoo version may still send a telemetry-disabled event with runtime/user metadata. Do not assume complete offline operation or add real customer information to the sample data.

## 3. Credentials and local results

Copy the safe template, then open **the new root `.env` file in your editor** and fill in `OPENAI_API_KEY` with your own project-scoped key. Never paste it into a screenshot or print it in a terminal. Do not share the filled file.

macOS/Linux:

```bash
cp .env.example .env
chmod 600 .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
```

The Python scripts and Promptfoo load the root `.env`. Direct Python snippets in the guided Agents lab also load it explicitly. Use a fresh terminal, without inherited `OPENAI_API_KEY`, `OPENAI_BASE_URL`, model overrides, or vector-store IDs from another project. A project-scoped key normally needs no organization or project override. If your organization requires one, use the environment names supported by the installed SDK (`OPENAI_ORG_ID`, `OPENAI_PROJECT_ID`) and configure Promptfoo consistently; verify the selected project before running.

From the bundle root, check installation and whether a key is present **without revealing it**:

```bash
python scripts/check_setup.py
```

This performs local checks only. “Key present” does not establish model access. Before paid steps, confirm the selected API project allows the specified models and endpoints. A 401 means authentication failed; a 403 or model-not-found error may mean missing model/project permission. Resolve access instead of silently substituting a model.

The bundle launcher fixes `PROMPTFOO_CONFIG_DIR` to this bundle’s `.promptfoo` directory for both eval and viewer commands. Set `PROMPTFOO_PYTHON` again after opening a new terminal. This keeps local results separate from other labs.

## 4. Complete the guided exercise

Read [the complete guided lab](labs/lab01_evals_guided/README.md), beginning at Task 2 after completing setup here. It preserves the original sequence, code blocks, rubrics, and checkpoints. All its commands run from this bundle root. A bare filename such as `tools.py` means the file inside `labs/lab01_evals_guided/`.

**Models:** `gpt-5` for the two graders. See [GPT-5 availability](https://developers.openai.com/api/docs/models/gpt-5). The external course currently specifies `gpt-5.6-terra`; this bundle deliberately retains the repository model pending course-owner reconciliation.

**Sequence:** Explore the 11-row `sample_01.jsonl`; add the relevance rubric, directness rubric, and exact tool-name assertion; validate after each addition; run the eval; inspect the viewer and reflect. The starter `promptfooconfig.yaml` has **zero assertions**. The separately named `promptfooconfig.solution.yaml` is the existing complete reference. `run.py` launches that reference and therefore is not the command to use while doing the starter exercise.

A normal complete eval makes 22 paid grader calls (11 rows × 2 rubrics). The deterministic assertion and echo provider are local. Preserve the existing 6/7 relevance threshold, 3/3 directness threshold, boolean pass instructions, and exact tool equality check. For the optional equality failure case, use a separate custom dataset with a different `expected_tool`; keep the supplied sample intact.

This bundle includes only this guided lab, `sample_01.jsonl`, package initializers, the referenced Promptfoo illustration, setup files, and provenance. The legacy evaluation helper is not used and is omitted.


Each step that invokes an OpenAI model incurs API usage. Dependency installation, syntax checks, data inspection, and `promptfoo validate config` do not make model calls. The local `echo` provider returns existing answers; the `llm-rubric` assertions make the paid grader calls. A viewer session adds no grader calls. Repeating an eval with `--no-cache` charges for fresh grading; transient retries can add calls. Reasoning tokens also count toward output usage.

Prices and availability can change. Check the [official API pricing page](https://developers.openai.com/api/docs/pricing) and project usage before running. If you run File Search, it currently lists $2.50 per 1,000 tool calls and $0.10 per GB per day of storage after the free allowance; do not assume your project has unused free storage.

## 5. Check your results

- Use the step-specific checkpoints in the guide. Inspect actual output, not just process exit status; some original runners catch errors and still exit successfully.
- Keep runtime/API errors separate from ordinary failed assertions. The supplied data contains deliberately questionable answers; model graders may disagree. There is no required aggregate pass count.
- Verify each expected row exists, generated answers are nonempty, and there are no `[ERROR]` outputs before evaluating. A guardrail tripwire on deliberately unsafe/off-topic input is an expected learning outcome.
- Inspect the latest local Promptfoo run and record one strong example, one failure or uncertain judgment, and one improvement. Answer the guide's reflection questions. No live facilitator is needed for completion.
- The `MANIFEST.sha256` file describes the untouched bundle. Your exercises will intentionally change starter files; keep the downloaded ZIP as your clean recovery copy.

Portable JSONL preview (replace the filename as needed):

```bash
python -c "import json; from pathlib import Path; p=next(Path('labs/data').glob('sample_*.jsonl')); print(json.dumps(json.loads(p.read_text(encoding='utf-8').splitlines()[0]), indent=2))"
```

## Troubleshooting

- `No module named labs`: return to the bundle root and use `python -m labs...`, with the bundle's environment active. Do not set `PYTHONPATH` to a repository checkout.
- Missing dependency: rerun `python -m pip install -r requirements.txt` with the same Python interpreter used by Promptfoo.
- Python/Pydantic `TypedDict` error: use Python 3.12 or 3.13 and recreate the environment.
- Invalid YAML: compare indentation with the guide/reference; validate after each edit.
- Missing generated dataset: finish the generation task first. No previous results ship in this ZIP.
- Promptfoo viewer appears empty: use the same `PROMPTFOO_CONFIG_DIR` as the eval, and complete a run first.
- API rate/quota errors: check your project's usage and limits; wait before retrying. Do not repeatedly relaunch entire workflows.
- Expected starter gaps: complete the explicit TODOs first. A placeholder response or missing tool before its implementation task is not evidence of an installation error.

Windows commands have been reviewed but not runtime-tested on Windows. Linux commands likewise have not been executed on Linux; the local verification host is macOS.

## Cleanup

Stop the viewer with Ctrl+C. Save any exercise notes you need. Delete only this bundle's `.promptfoo` directory to remove local Promptfoo results, and this bundle's `.venv` to remove its installed environment. Delete your filled `.env`, revoke the lab key in your API project when no longer needed, and clear shell overrides by closing the terminal. Keep unrelated project keys, results, files, and resources untouched.

For Agents/RAG, API responses and traces may remain in the project's platform history according to its data settings; deleting local files does not delete server-side history. The RAG-specific resource cleanup below is required separately.

This exercise creates no vector stores or uploaded FAQ files. Remove only its local results when finished.


See [attribution and license](ATTRIBUTION.md), [known issues](KNOWN-ISSUES.md), and `SOURCE.json` for source provenance.
