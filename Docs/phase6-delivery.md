# Phase 6 — Delivery & MVP Checklist

> Hardening, testing, and fellowship demo readiness.

---

## Error matrix verification (architecture §9)

| Failure | Expected behavior | Automated test |
|---------|-------------------|----------------|
| Invalid user input | Validation errors; no Groq call | `test_hardening.py::TestErrorMatrixInvalidInput` |
| Zero filter matches | Empty message; `llm_used=False` | `test_hardening.py::TestErrorMatrixZeroMatches` |
| Malformed Groq JSON | Fallback ranking | `test_hardening.py::TestErrorMatrixMalformedJson` |
| Hallucinated restaurant ID | Drop invalid rows | `test_hardening.py::TestErrorMatrixHallucinatedIds` |
| HF download fails | Startup error (manual / integration) | `test_ingestion` (integration) |
| Groq timeout / rate limit | Retry + fallback (implemented in `recommend.py`) | Manual / mock exception |
| Groq API key missing | UI + CLI error message | Manual: start app without `.env` key |

Run automated suite:

```bash
python -m pytest -v -m "not integration"
```

---

## Final MVP checklist

| Item | Status |
|------|--------|
| Data loads from Hugging Face (or `data/cache.parquet`) | ✅ |
| User sets location, budget, cuisine, min rating, additional prefs | ✅ Streamlit UI |
| Filter runs before Groq; candidate count logged | ✅ orchestrator metadata |
| Groq ranks and explains; optional summary | ✅ |
| UI shows name, cuisine, rating, cost, explanation | ✅ |
| Fallback when Groq/parse fails | ✅ |
| `GROQ_API_KEY` not in repo (`.gitignore` + `.env.example` only) | ✅ |
| Docs: context, architecture, implementation-plan | ✅ |

---

## Demo (2-minute fellowship walkthrough)

```bash
# Live Groq (requires .env)
python scripts/demo.py

# Offline
python scripts/demo.py --mock
```

**Script flow:** load store → Bangalore + medium + Italian → top 3 with explanations.

> Implementation plan example uses Delhi; this dataset is **Bangalore-centric**. Demo uses Bangalore for real results.

---

## Quick commands

| Command | Purpose |
|---------|---------|
| `make install` | Install dependencies |
| `make test` | Unit tests (no network) |
| `make demo` | Fellowship demo script |
| `make ui` | Streamlit app |
| `python -m pytest -v` | Full test run |

---

## Success criteria (context.md)

| Criterion | Verification |
|-----------|--------------|
| End-to-end ingest → preferences → filter → Groq → display | `tests/test_orchestrator.py` + UI + `scripts/demo.py` |
| Grounded recommendations | `test_hardening.py::TestSuccessCriteriaGrounded` |
| Personalized explanations | Manual: run demo; check explanation mentions prefs |
| Readable output | Streamlit cards + CLI output |

---

## Manual UI scenarios

See [phase5-ui-test-plan.md](phase5-ui-test-plan.md).

---

## Docker (optional)

```bash
docker build -t zomato-ai .
docker run -p 8501:8501 -e GROQ_API_KEY=your_key -v ./data:/app/data zomato-ai
```

Mount `data/cache.parquet` to avoid re-downloading the dataset inside the container.
