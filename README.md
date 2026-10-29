# Interview Studio

A local Python application for role-specific interview design and rubric-based interview practice.

## Start here (Windows / VS Code)

1. Extract the ZIP. Open the `interview_generator` folder in VS Code.
2. Copy your existing private `.env` file into this folder, beside `app.py`. If you do not have one, copy `.env.example` to `.env` and fill in `GROQ_API_KEY` locally. The filename must be `.env`, not `env.py` or `.env.txt`.
3. Open Terminal > New Terminal and run:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Python 3.10+ required. No key entry appears in the browser. API configuration loads from the `.env` beside `app.py`. Stop with Ctrl+C and rerun the last command to restart.

### Updating an existing installation

Keep a backup of your existing project. You can use this extracted project as a fresh folder and copy only your private `.env` into it. Do not copy the old `.venv` or old Python files into the new project. If using the existing folder instead, replace app.py and core.py, add storage.py, reports.py, session_tools.py and assets/, replace requirements.txt and install requirements again. Preserve your `.env` and any existing data/ folder.

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

## Features

- Replace one question while preserving the rest of the interview. Replacement keeps the original type and difficulty; confirmation is required because its saved answer and feedback are cleared on success.
- Search question text and competencies without changing saved content or exports.
- Restore a JSON export as a new session. Imports validate question structure, rubric totals, answer references and feedback evidence; existing sessions are never overwritten. Maximum backup size: 1 MB.

- Role, job description, skill, seniority, difficulty and interview-type controls.
- One to five questions per API batch; append batches up to 30 questions per session.
- Expected-answer guides, two follow-ups and three question-specific scoring criteria totaling 10 points per question.
- History passed to generation; exact and near-duplicate text checks reject repeat batches without changing the saved session. These heuristics cannot guarantee semantic uniqueness.
- Practice mode hides answer guides. Save answers or request rubric-based AI feedback.
- Feedback includes per-criterion scores, exact answer evidence, missing points, next steps and an improved answer example. Scores and evidence quotes are validated.
- SQLite saves interviews, settings, answers and feedback automatically after successful actions. Reopen or delete them in the sidebar.
- Changing and saving an answer clears its old feedback; unsaved edited answers hide stale feedback.
- PDF export with answer-guide and practice-data inclusion controls, Markdown guides and full session JSON.
- Generation/evaluation errors preserve previously saved work.

## How to use

1. Create an interview with a role and skills or a JD.
2. Read a question, write your answer, then Save answer or Evaluate answer. Typing alone does not persist it.
3. Turn off practice mode to see answer guidance and rubrics.
4. Click Generate more to append questions using the active interview's saved settings. The new-interview form does not change the active session.
5. Open a saved interview from the sidebar after restarting.
6. To replace a weak question, expand Replace this question and confirm. To restore a portable backup, export JSON and use Restore a JSON backup in the sidebar.
7. Prepare a PDF and download it. Downloads are optional. PDF content matches its inclusion checkboxes. Markdown includes guides; JSON includes saved answers and feedback.

## Implementation

| Module | Responsibility |
|---|---|
| app.py | Streamlit UI, state, action handling |
| core.py | Typed requests/output, prompts, Groq calls, validation, similarity checks |
| session_tools.py | Validated backup restoration and atomic question replacement |
| storage.py | Parameterized SQLite operations with a whitelist of stored fields |
| reports.py | Escaped, wrapped PDF output using ReportLab and a bundled Unicode font |
| evaluation/ | Twelve role/level test prompts and an opt-in live evaluation runner |
| tests/ | Unit and Streamlit integration checks |

Flow: role/JD -> validated request -> Groq structured output -> semantic validation -> SQLite session -> answer -> Groq feedback -> evidence/score checks -> SQLite -> report.

Groq hosts the selected model (default `openai/gpt-oss-120b`). Only a Groq key is required. No OpenAI API key or billing is used. Model access and free-tier quotas can change. No vector database, agent framework or fine-tuning is needed for this bounded workflow.

## Tests and evaluation

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe evaluation/run_evaluation.py
```

The default evaluator validates the 12 test prompts without API calls. To collect real model outputs and a human review sheet using your own key:

```powershell
.venv\Scripts\python.exe evaluation/run_evaluation.py --live --limit 3
```

The live command consumes quota. It saves outputs and `review.csv` under evaluation/live_results/. Rate relevance, difficulty, rubric specificity and technical accuracy honestly. Do not report input validation or mocked tests as LLM answer quality. See EVALUATION_REPORT.md for measured checks and outstanding live evaluation.

## Privacy and limitations

This is a single-user local application, not an authenticated multi-user service. Anyone with access to the running local app can see its saved sessions. Do not publish it as-is.

Keys stay in `.env`, outside source code and database storage. `.gitignore` excludes secrets, databases and live results. Do not share a ZIP containing your private `.env` or data/ folder. Job descriptions and candidate answers are sent to Groq on generation/evaluation. Local sessions are plaintext SQLite, not encrypted. Save only appropriate data. Delete a session from the sidebar to remove its database row; deletion is not guaranteed forensic erasure of SQLite pages, backups or downloaded reports.

Schema correctness and exact evidence quotes do not prove factual correctness, fair assessment or appropriate scoring. Review AI feedback; accept equivalent valid approaches. This app does not make hiring recommendations. Duplicate checks are lexical heuristics, so different wording can still repeat a concept. Long JDs, many previous questions and free-tier token limits can cause generation failures. Use smaller batches or start another focused session.

Tests mock external APIs. Live Groq testing of this final package and human ratings remain the submitter's responsibility. No API key is included.

## Included submission material

- PROJECT_REPORT.md: problem, objectives, architecture and design decisions.
- EVALUATION_REPORT.md: actual engineering checks, limitations and quality evaluation protocol.
- DEMO_GUIDE.md: short demo sequence and viva talking points.
- examples/sample_report.pdf: clearly labelled handcrafted export demonstration, not live model evidence.
- assets/FONT_LICENSE.txt: bundled DejaVu font license.

## Source-backed practice and expanded testing

Restore `examples/source_backed_session.json` from the sidebar to practise 12 manually authored questions grounded in official Python, PostgreSQL and scikit-learn documentation. Source URLs are in the session assumptions. These are not claimed to be actual HCL questions.

```powershell
.venv\Scripts\python.exe evaluation/test_grounded.py
.venv\Scripts\python.exe evaluation/evaluate_answers.py --live --limit 1
```

The first command runs eight local reference checks without an API key. The second makes three live feedback requests with your local key. All twelve questions require 36 live calls (`--limit 12`). The 29-test suite includes real SQLite persistence, concurrency, rollback and process-reopen tests. See EVALUATION_REPORT.md and the raw result files for the measured results and remaining model-quality work.
