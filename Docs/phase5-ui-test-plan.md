# Phase 5 UI — Manual Test Plan

Run the app from project root:

```bash
streamlit run src/ui/app.py
```

Ensure `.env` contains `GROQ_API_KEY`.

---

## Scenario 1 — Happy path

| Step | Action | Expected |
|------|--------|----------|
| 1 | Start app | Sidebar shows restaurant count; no load error |
| 2 | Location: **Bangalore**, Budget: **Medium**, Cuisine: **North Indian** | Form accepts input |
| 3 | Click **Get recommendations** | Spinner visible during Groq call |
| 4 | Review results | ≥1 card with name, cuisine, rating, cost, AI explanation |
| 5 | Check summary | Optional summary banner above cards |
| 6 | Check metadata | Candidate count and Groq latency shown |

---

## Scenario 2 — Empty results

| Step | Action | Expected |
|------|--------|----------|
| 1 | Location: **Bangalore**, Budget: **Low**, Cuisine: **French**, Min rating: **5.0** | — |
| 2 | Submit | Warning empty state with tips (no crash) |
| 3 | Verify | No recommendation cards; `llm_used` should be false (no Groq call) |

---

## Scenario 3 — Fallback (optional)

Simulate by temporarily invalidating the API key or disconnecting network, then submit a valid query.

| Expected |
|----------|
| Yellow fallback banner |
| Restaurants still listed with template explanations |
| App does not crash |

---

## Acceptance checklist

- [ ] All five fields on each card: name, cuisine, rating, cost, explanation
- [ ] Validation errors show inline (e.g. empty location if forced)
- [ ] Loading spinner during recommendation request
- [ ] App usable without editing code
