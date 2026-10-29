# Three-minute demonstration

Before presenting: configure your private .env, install requirements, run tests, and perform one live generation and evaluation with your key. Keep a saved session ready in case the provider is unavailable. Do not show the key on screen.

1. **0:00-0:30 - Problem and inputs.** Explain that the app combines role-specific questions with explicit answer evidence and scoring criteria. Choose a role, experience and three focused skills; generate three questions.
2. **0:30-1:00 - Interview quality.** Show question type and difficulty. Turn practice mode off briefly to show the expected answer, follow-ups and criteria totaling ten points.
3. **1:00-1:40 - Practice.** Turn practice mode on, write an answer and evaluate it. Show the per-criterion scores, exact evidence quote, missing points and next practice steps. Explain that this is coaching feedback, not a hiring decision.
4. **1:40-2:10 - Extend.** Generate one more question. Show that the earlier questions and answer remain. Explain history-aware prompting and lexical duplicate rejection honestly.
5. **2:10-2:35 - Persistence.** Open the saved interview from the sidebar. Explain local SQLite storage and why keys are excluded.
6. **2:35-3:00 - Export and evidence.** Prepare and download a PDF. Explain export privacy choices, automated tests and the separate live review protocol.

## Likely viva questions

- **Why use Pydantic?** It validates structure and provides the output schema; business checks enforce rubric totals and evidence bounds.
- **Is this an agent?** No. It is a controlled LLM workflow. It does not need autonomous tool selection.
- **How are duplicates prevented?** Previous questions enter the prompt, then normalization, sequence similarity and word overlap screen results. Semantic repeats remain possible.
- **How reliable are scores?** They are advisory. Range and quote checks establish traceability, not correctness. Human calibration remains necessary.
- **What happens on an API failure?** A readable error is shown and saved work is preserved.
- **Where are secrets?** In a private .env; not in prompts, exports or database records.
- **Can it be hosted?** Not safely as a multi-user service without authentication, user isolation and abuse controls.
- **What did you evaluate?** Report actual automated results separately from human ratings of real model outputs. Never claim mocked tests establish generation accuracy.
