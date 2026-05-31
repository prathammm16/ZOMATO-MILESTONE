# Zomato AI Restaurant Recommendation System

AI-powered restaurant recommendations for the **Project Manager Fellowship** milestone.  
Combines the [Zomato Hugging Face dataset](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) with **Groq** LLM ranking and natural-language explanations.

---

## Features

- Load & normalize ~40k+ restaurants (cached locally as Parquet)
- Filter by **location**, **budget** (low/medium/high), **cuisine**, **minimum rating**
- **Groq** ranks top picks and explains why each fits
- **Streamlit UI** for end-to-end demo
- **Fallback** to filter-sorted results if Groq or JSON parsing fails

---

## Quick start

### 1. Prerequisites

- Python 3.10+
- [Groq API key](https://console.groq.com) (free tier available)

### 2. Install

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
```

### 3. Configure `.env`

```env
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

### 4. First run (loads dataset or cache)

```bash
python scripts/demo.py --mock    # offline smoke test
python scripts/demo.py           # live Groq demo
streamlit run src/ui/app.py      # web UI
```

First Hugging Face download is ~574 MB. Subsequent runs use `data/cache.parquet`.

---

## Sample preferences (evaluator)

| Field | Example |
|-------|---------|
| Location | **Bangalore** (or neighborhood: **BTM**, **Banashankari**) |
| Budget | **medium** |
| Cuisine | **Italian** or **North Indian** |
| Min rating | **3.5** |

> This dataset is mostly **Bangalore** restaurants. Use Bangalore for live demos.

---

## Architecture

```
User preferences → validate → filter (max 20) → Groq LLM → parse → UI / CLI
                      ↑                              ↓
               Restaurant store ← HF dataset / cache   fallback if error
```

| Layer | Path |
|-------|------|
| Data | `src/data/` |
| Filter | `src/filtering/` |
| Groq LLM | `src/llm/` |
| Orchestrator | `src/api/orchestrator.py` |
| UI | `src/ui/app.py` |

Full design: [Docs/architecture.md](Docs/architecture.md)

---

## Commands

```bash
# Tests (no network)
python -m pytest -v -m "not integration"

# Fellowship demo (~2 min script)
python scripts/demo.py

# CLI pipeline
python -m src.api --location Bangalore --budget medium --cuisine Italian

# Streamlit UI
streamlit run src/ui/app.py

# FastAPI backend + React frontend
uvicorn src.api.server:app --host 127.0.0.1 --port 8000 --reload
cd frontend && python -m http.server 5173 --bind 127.0.0.1

# Optional Vite dev server if npm is available
cd frontend && npm install && npm run dev
```

**Makefile shortcuts:** `make install`, `make test`, `make demo`, `make ui`, `make react-ui`

---

## Dataset attribution

- **Source:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) on Hugging Face
- **License:** See dataset card on Hugging Face
- **Usage:** Educational / fellowship milestone only

---

## Project structure

```
ZOMATO-MILESTONE/
├── src/data/          ingestion, store, models
├── src/filtering/     validation, candidate filter
├── src/llm/           Groq client, prompts, parser
├── src/api/           get_recommendations() orchestrator
├── src/ui/            Streamlit app
├── frontend/          React + Vite frontend
├── config/            settings from .env
├── scripts/           demo.py, smoke tests
├── tests/             pytest suite
├── Docs/              context, architecture, plans
├── data/cache.parquet # generated (gitignored)
├── .env.example
└── requirements.txt
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [Docs/context.md](Docs/context.md) | Problem & workflow |
| [Docs/architecture.md](Docs/architecture.md) | System design (Groq) |
| [Docs/implementation-plan.md](Docs/implementation-plan.md) | Phase-wise plan |
| [Docs/edge-case.md](Docs/edge-case.md) | Edge case catalog |
| [Docs/phase5-ui-test-plan.md](Docs/phase5-ui-test-plan.md) | UI manual tests |
| [Docs/phase6-delivery.md](Docs/phase6-delivery.md) | MVP checklist & delivery |

---

## Security

- Never commit `.env` or API keys (see `.gitignore`)
- Copy from `.env.example` only

---

## Docker (optional)

```bash
docker build -t zomato-ai .
docker run -p 8501:8501 -e GROQ_API_KEY=your_key -v ./data:/app/data zomato-ai
```

---

## Implementation status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Foundation | ✅ |
| 1 | Data pipeline | ✅ |
| 2 | Filter & preferences | ✅ |
| 3 | Groq LLM integration | ✅ |
| 4 | Orchestrator | ✅ |
| 5 | Streamlit UI | ✅ |
| 6 | Hardening & delivery | ✅ |
