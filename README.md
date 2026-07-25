# Incident AI

LangGraph workflow matching the supplied design:

`intake → incident lookup → create/history → investigation plan → retrieve evidence/history/knowledge/similar cases → analysis loop → report`

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate - make sure you are in the right directory.
or source /Users/farnazmozhgani/Desktop/Incident-AI/.venv/bin/activate
python -m pip install -r requirements.txt
.venv/bin/python agent_framework.py "Service: Payments\nHigh error rate after deployment" --source text
# Or submit a .pdf / .txt file:
.venv/bin/python agent_framework.py --file ./incident.pdf
```

The default database is `data/incidents.db` (SQLite: free, local, and no account required). It is created automatically.

## Database data and inspection

Add some safe local demo data (two past incidents, their evidence, and two runbooks):

```bash
.venv/bin/python agent_framework.py --seed-demo
.venv/bin/python agent_framework.py --list
.venv/bin/python agent_framework.py --show 1
```

The `--list` output includes each incident ID. `--show ID` returns the full record, history, evidence, and generated reports. Add real evidence after submission with:

```bash
.venv/bin/python agent_framework.py --add-evidence 1 --evidence-source "Datadog" --evidence-content "API 5xx rate reached 18% at 10:42 UTC"
```

## Custom tools

`incident_ai/tools.py` contains the tools that agents use: incident lookup, incident creation, history and evidence retrieval, knowledge search, similar-case search, and report persistence. `incident_ai/repository.py` is the only SQLite-specific layer, so it can later be swapped for Postgres/Supabase without rewriting the graph.

## Gemini configuration

To use Gemini Flash, obtain a Google AI Studio key and start the app from a terminal where the key is set:

Make sure to install the gemini-genai library - pip install google-genai --only-binary=:all:



```bash
export GEMINI_API_KEY="your-key"
export GEMINI_MODEL="gemini-3.6-flash"
.venv/bin/streamlit run app.py
```

The application uses only the official `google-genai` SDK and Gemini's Interactions API. It will show a configuration error if `GEMINI_API_KEY` is missing.

The CLI extracts text from normal PDFs with `pypdf`. Scanned PDFs need an OCR step before submission.

## Web dashboard

Install dependencies, then run:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

The dashboard submits incidents to the same LangGraph workflow, lets you inspect IDs and full records, add evidence, browse runbooks, and seed demo cases.
