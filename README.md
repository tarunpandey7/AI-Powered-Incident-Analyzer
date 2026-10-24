# SupportMate AI — Technical Support Assistant

## Overview
SupportMate AI is a small prototype that helps L1/L2 support engineers investigate common issues by retrieving guidance from a simulated knowledge base. It shows the source entries behind its recommendations and responds cautiously when it cannot find a good match.

## Features
- Plain-language issue input in a Streamlit chat-like interface
- Six sample knowledge-base entries covering API 500 errors, database connectivity, login failures, slow applications, 401/403 access errors, and file-upload failures
- Lightweight keyword/synonym retrieval with ranked results
- Troubleshooting checks, documented resolution guidance, escalation team, and source ID
- Unknown-issue handling that asks for clarifying information rather than inventing a fix
- Optional OpenAI API response generation grounded in retrieved entries
- Safe fallback response template if no API key is configured or AI generation fails

## Architecture
1. User describes an issue.
2. Retrieval code scores the query against knowledge-base titles, symptoms, checks, resolutions, and notes.
3. The top relevant entries are shown to the user.
4. If `OPENAI_API_KEY` is configured, an LLM summarizes the retrieved entries under a grounding-focused prompt.
5. Without an API key, a deterministic template uses the documented fields directly.
6. Weak or missing matches trigger a clarification response.

## Requirements
- Python 3.10 or newer recommended
- pip
- Optional: OpenAI API key for LLM-generated summaries

## Setup
### Windows (PowerShell)
```powershell
cd technical_support_ai_assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

### macOS/Linux
```bash
cd technical_support_ai_assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Optional AI setup
Set the API key as an environment variable before launching the app. Do not hardcode keys in source code or commit them to GitHub.

PowerShell:
```powershell
$env:OPENAI_API_KEY="your-key-here"
$env:OPENAI_MODEL="gpt-4o-mini"
streamlit run app.py
```

macOS/Linux:
```bash
export OPENAI_API_KEY="your-key-here"
export OPENAI_MODEL="gpt-4o-mini"
streamlit run app.py
```

If no key is set, the prototype still runs and uses its local source-grounded template. API usage may incur charges depending on your account and provider.

## Demo scenarios
1. **Known issue:** `The payment API is returning a 500 error`
   - Expected: Payment API entry, log/dependency/deployment checks, backend escalation, and KB-001 source.
2. **Known issue:** `My application cannot connect to the database`
   - Expected: database connectivity checks and KB-002 source.
3. **Access issue:** `Our API returns 401 unauthorized`
   - Expected: token/scope/permission checks and KB-005 source.
4. **Unknown issue:** `The printer is making a strange noise`
   - Expected: no confident source match; asks for more detail instead of inventing a fix.
5. **Safety check:** do not enter passwords, tokens, API keys, or customer data.

## Testing checklist
- [ ] Each known example retrieves the expected entry near the top.
- [ ] A totally unrelated issue does not produce a confident resolution.
- [ ] Source IDs and source details are visible.
- [ ] The app works without an API key.
- [ ] With an API key, generated text stays within retrieved knowledge-base facts.
- [ ] Secrets are not included in prompts or committed files.

## AI tools/models
- **Retrieval:** local keyword-overlap scoring with a small synonym map; no external service required.
- **Optional generation:** OpenAI Chat Completions API; default model name `gpt-4o-mini`, configurable via `OPENAI_MODEL`.
- **Development assistance:** disclose any AI coding assistant used during implementation and explain which parts you reviewed, tested, and modified yourself.

## Assumptions
- The included knowledge base is fictional sample content.
- Escalation team names are illustrative.
- Resolution guidance is general and must be verified against an organization's actual runbooks.
- HTTP 500 errors can have multiple causes; the assistant recommends investigation rather than asserting a single root cause.

## Limitations
- Keyword retrieval may miss paraphrases or rank similar issues incorrectly.
- The sample knowledge base is small and not connected to live monitoring, logs, ticketing, or production systems.
- The LLM can still make mistakes; the prompt and source display reduce risk but do not guarantee correctness.
- Authentication, access controls, observability, audit logging, evaluation metrics, and production hardening are out of scope.
- Never send sensitive production data or secrets to an external model.

## Suggested improvements
- Replace keyword retrieval with embeddings and a vector store.
- Add a larger reviewed knowledge base and retrieval-quality tests.
- Track feedback (helpful/not helpful) and evaluate retrieval accuracy.
- Add role-based access and approved internal-document connectors if moving beyond a demo.
