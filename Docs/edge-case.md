# Edge Case Catalog

> **Zomato AI Restaurant Recommendation System**  
> Companion to [context.md](context.md), [architecture.md](architecture.md), and [implementation-plan.md](implementation-plan.md).

This document lists **edge cases** across the pipeline—ingestion → preferences → filter → LLM → display—with **expected behavior**, **implementation guidance**, and **test hints**. Use it during development (Phase 6) and QA.

**Priority legend:** `P0` = must handle for MVP · `P1` = should handle · `P2` = nice to have / document only

---

## Quick Reference Matrix

| ID range | Layer | Count |
|----------|-------|-------|
| EC-D* | Data ingestion & store | 18 |
| EC-U* | User input & validation | 14 |
| EC-F* | Candidate filter | 16 |
| EC-L* | LLM (prompt, client, parser) | 20 |
| EC-O* | Orchestrator | 8 |
| EC-P* | Presentation (UI) | 12 |
| EC-S* | Security & config | 6 |
| EC-X* | Cross-cutting / operational | 8 |

---

## 1. Data Ingestion & Store (EC-D)

| ID | Edge case | Trigger | Expected behavior | Priority |
|----|-----------|---------|-------------------|----------|
| EC-D01 | Hugging Face download fails | Network down, HF outage, auth error | Block startup; show clear error: *"Could not load dataset. Check network or use local cache."* Do not run with empty store. | P0 |
| EC-D02 | Dataset version or schema changed | HF column rename / missing column | Map with fallback column aliases; log unmapped fields; fail startup if required fields (`name`, `location`, `rating`) missing entirely. | P0 |
| EC-D03 | Empty dataset after load | Zero rows returned | Fail startup with error; no silent empty app. | P0 |
| EC-D04 | All rows invalid after validation | Every row missing `name`, `location`, or `rating` | Fail startup or warn with 0 valid rows; do not proceed. | P0 |
| EC-D05 | Partial invalid rows | Some rows missing fields | Drop invalid rows; log count (`loaded`, `kept`, `dropped`). | P0 |
| EC-D06 | Missing `cost` column | Cost field absent or all null | Assign `budget_tier = medium` for affected rows; log warning once. | P1 |
| EC-D07 | Non-numeric cost / rating | Strings like `"$500"`, `"4.5/5"`, `"-"` | Strip symbols; parse float; on failure set `rating=0` or drop row per policy (document in logs). | P1 |
| EC-D08 | Rating out of range | `rating > 5` or `< 0` | Clamp to `[0, 5]` or drop row; log anomaly count. | P1 |
| EC-D09 | Duplicate restaurant names same location | Multiple rows same name+city | Keep all with unique internal `id` (row index or hash); do not dedupe unless product requires. | P2 |
| EC-D10 | Location string inconsistency | `"delhi"`, `"Delhi NCR"`, `"New Delhi"` | Normalize to canonical form where possible (trim, casefold); maintain alias map for filter; unknown strings still stored. | P1 |
| EC-D11 | Cuisine as single string vs list | `"Italian, Chinese"` vs `["Italian"]` | Split on comma/semicolon; trim; lowercase tokens for matching. | P0 |
| EC-D12 | Empty cuisine field | `cuisines = []` | Keep row; cuisine filter skipped for that row unless user specifies cuisine (row excluded). | P1 |
| EC-D13 | Cost percentiles degenerate | All costs identical | All rows get same `budget_tier` (e.g. `medium`); log once. | P1 |
| EC-D14 | Very few rows per location | Location has 1–2 restaurants | Filter still works; LLM may get 1–2 candidates only. | P1 |
| EC-D15 | Local cache corrupt or stale | Bad Parquet/JSON cache file | Delete cache and re-download; or fail with path to cache file. | P1 |
| EC-D16 | Cache exists but HF updated | User expects fresh data | Document: delete cache to refresh; optional `FORCE_REFRESH=true` env. | P2 |
| EC-D17 | Memory pressure on load | Huge dataset on low-RAM machine | Use streaming/chunked load if needed; for MVP dataset size, in-memory OK. | P2 |
| EC-D18 | `get_by_ids` partial match | LLM returns IDs not in store | Return only found IDs; log missing IDs (see EC-L08). | P0 |

### Implementation notes (Data)

```python
# EC-D06: missing cost
budget_tier = derive_tier(cost) if cost is not None else "medium"

# EC-D10: location normalize (example)
def normalize_location(s: str) -> str:
    return s.strip().casefold()
```

**Tests:** `test_ingestion` — dropped rows, tier assignment, empty load failure.

---

## 2. User Input & Validation (EC-U)

| ID | Edge case | Trigger | Expected behavior | Priority |
|----|-----------|---------|-------------------|----------|
| EC-U01 | Empty location | User submits blank location | Validation error: *"Location is required."* No filter/LLM call. | P0 |
| EC-U02 | Whitespace-only location | `"   "` | Treat as empty (EC-U01). | P0 |
| EC-U03 | Unknown location | City not in dataset | Validation warning OR filter returns empty (EC-F01); suggest picking from dropdown list. | P0 |
| EC-U04 | Missing budget | Budget not selected | Validation error: *"Budget is required (low, medium, high)."* | P0 |
| EC-U05 | Invalid budget value | `"cheap"`, `123`, injection string | Reject; only accept `low` \| `medium` \| `high`. | P0 |
| EC-U06 | `min_rating` below 0 or above 5 | Slider bug or API tampering | Clamp or reject with validation message. | P0 |
| EC-U07 | `min_rating` omitted | Optional field null | Default to `0.0` (no rating filter). | P0 |
| EC-U08 | `min_rating` very high (e.g. 4.9) | User sets unrealistic threshold | Valid input; filter may return empty (EC-F03) — show empty state, not error. | P1 |
| EC-U09 | Cuisine empty | User leaves cuisine blank | Skip cuisine filter; match location + budget + rating only. | P0 |
| EC-U10 | Cuisine typo | `"Itallian"` vs `"Italian"` | Partial/substring match if possible; else fewer results; empty state with hint to try broader term. | P1 |
| EC-U11 | Cuisine with special characters | `"Café"`, `"South Indian"` | Sanitize for filter (case-insensitive substring); no code execution. | P1 |
| EC-U12 | Very long `additional_preferences` | 10k characters pasted | Truncate to max length (e.g. 500 chars) before prompt; warn in UI if truncated. | P1 |
| EC-U13 | Additional preferences only (no structured match) | Keywords not in dataset metadata | No extra filter effect; pass text to LLM in prompt for reasoning only. | P1 |
| EC-U14 | Duplicate rapid submits | User double-clicks Submit | Disable button during request; ignore second in-flight call or queue one. | P1 |

### Implementation notes (User)

```python
# EC-U07
min_rating = preferences.min_rating if preferences.min_rating is not None else 0.0

# EC-U12
MAX_ADDITIONAL_LEN = 500
additional = (prefs.additional_preferences or "")[:MAX_ADDITIONAL_LEN]
```

**Tests:** Validator unit tests for each rejection path; no side effects on invalid submit.

---

## 3. Candidate Filter (EC-F)

| ID | Edge case | Trigger | Expected behavior | Priority |
|----|-----------|---------|-------------------|----------|
| EC-F01 | Zero matches after all filters | Strict location + budget + cuisine + rating | Return `candidates=[]`, `empty_reason` with tips: relax cuisine, lower `min_rating`, or try nearby location label. **Do not call LLM.** | P0 |
| EC-F02 | Single candidate | Only one restaurant matches | Pass 1 candidate to LLM; rank top 1; UI shows one card. | P0 |
| EC-F03 | High `min_rating` eliminates all | e.g. `min_rating=4.8` in sparse data | Same as EC-F01 empty state. | P0 |
| EC-F04 | Budget tier has no rows in location | No `low` restaurants in city | Empty state; suggest `medium` or `high`. | P1 |
| EC-F05 | Cuisine filter too strict | `"Italian"` matches none | Empty or partial; message: *"No Italian in {location}; try another cuisine."* | P1 |
| EC-F06 | Case-insensitive location match | User `"bangalore"`, data `"Bangalore"` | Match via normalized comparison. | P0 |
| EC-F07 | More than `MAX_CANDIDATES_TO_LLM` matches | 200 restaurants match | Sort by rating desc, cost asc; **cap at N** (default 20); log `truncated=true`. | P0 |
| EC-F08 | Exactly `MAX_CANDIDATES` matches | 20 matches, cap 20 | Send all 20 to LLM; monitor token size (EC-L15). | P1 |
| EC-F09 | Additional keyword filter on empty metadata | No text fields in dataset | Skip keyword filter; rely on LLM for nuance in prompt. | P1 |
| EC-F10 | Additional keyword eliminates all | Keyword too specific | Fall back to candidates before keyword step OR return empty with explanation. **Recommend:** apply keyword only if metadata exists; else LLM-only. | P1 |
| EC-F11 | Tie scores on sort | Same rating and cost | Stable sort by `id` or name for deterministic order. | P2 |
| EC-F12 | Location alias mismatch | User selects `"Delhi"`, data `"New Delhi"` | Maintain alias table in config; fuzzy match top location if exact fail (optional). | P1 |
| EC-F13 | User selects budget `low` but only high-cost venues in data | Data skew | Empty result; not a bug — communicate clearly. | P1 |
| EC-F14 | Filter with only location (minimal prefs) | Budget still required by validation | N/A if budget required; if optional in future, return all in location capped at N. | P2 |
| EC-F15 | Unicode in cuisine/location | Non-ASCII characters | UTF-8 safe string ops; no encoding crash. | P1 |
| EC-F16 | SQL/injection-style input in cuisine | `"; DROP TABLE` | Treat as literal substring; parameterized queries if using SQL store. | P0 |

### Implementation notes (Filter)

```python
# EC-F07
candidates = sorted(matches, key=lambda r: (-r.rating, r.cost))[:MAX_CANDIDATES_TO_LLM]
metadata["truncated"] = len(matches) > MAX_CANDIDATES_TO_LLM
```

**Tests:** `test_filter` — empty combo, single result, cap truncation, case insensitivity.

---

## 4. LLM — Prompt, Client, Parser (EC-L)

| ID | Edge case | Trigger | Expected behavior | Priority |
|----|-----------|---------|-------------------|----------|
| EC-L01 | Missing `LLM_API_KEY` | Env not set | Fail at startup or on first recommend with: *"Set LLM_API_KEY in .env"* | P0 |
| EC-L02 | Invalid API key | 401 from provider | User-facing: *"Recommendation service unavailable."* Log error; trigger fallback (EC-L17). | P0 |
| EC-L03 | LLM timeout | Request > 30s | Retry once; then fallback top 5 filter-sorted with template explanations. | P0 |
| EC-L04 | Rate limit (429) | Too many requests | Exponential backoff one retry; then fallback. | P0 |
| EC-L05 | Provider 5xx / service down | Server error | Same as EC-L03 fallback. | P0 |
| EC-L06 | Empty LLM response | Zero tokens returned | Fallback. | P0 |
| EC-L07 | Malformed JSON | Prose, markdown fences, trailing commas | Strip markdown code fences; regex extract JSON array; one retry prompt *"JSON only"*; else fallback. | P0 |
| EC-L08 | Hallucinated `restaurant_id` | ID not in candidate set | Drop those entries; log warning; if zero valid left → fallback. | P0 |
| EC-L09 | Duplicate ranks or missing ranks | Two `rank: 1` or gaps | Renumber by order in array or re-sort by rank; merge duplicates. | P1 |
| EC-L10 | Fewer than K recommendations returned | LLM returns 2 of 5 | Show what parsed; pad with next filter-sorted candidates without LLM explanation? **Prefer:** show 2 only; do not invent explanations. | P1 |
| EC-L11 | More than K recommendations | LLM returns 10 items | Take top K by rank; ignore rest. | P1 |
| EC-L12 | Empty `explanation` string | `"explanation": ""` | Use template: *"Matches your preferences for {location} and {budget}."* | P1 |
| EC-L13 | Explanation contradicts data | LLM says "5-star" but rating 3.2 | Display dataset rating on card (source of truth); explanation is advisory only. | P1 |
| EC-L14 | LLM invents restaurant name | Name in text but wrong ID | Parser merges by ID only; card shows dataset name, not LLM name. | P0 |
| EC-L15 | Prompt exceeds token limit | 20 large metadata blobs | Truncate per-candidate fields (drop `raw_metadata` from prompt); reduce N; log token estimate. | P0 |
| EC-L16 | Single candidate — LLM refuses to rank | "Only one option" | Accept single recommendation with explanation. | P1 |
| EC-L17 | Fallback path engaged | Any EC-L03–L07 failure | `metadata.fallback_used=true`; static explanations; `llm_used=false` or `true` with failed parse — document consistently. | P0 |
| EC-L18 | JSON with extra fields | Unknown keys in response | Ignore unknown keys; parse required fields only. | P1 |
| EC-L19 | Non-English user preferences | Hindi/regional input | Pass through to LLM; explanations may be English unless prompt requests user language. | P2 |
| EC-L20 | Content policy / safety filter block | Provider refuses prompt | Fallback + log; do not expose raw provider error to user. | P1 |

### Implementation notes (LLM)

```python
# EC-L07: extract JSON
import re
match = re.search(r"\[[\s\S]*\]", raw_response)
if match:
    data = json.loads(match.group())

# EC-L08: validate IDs
valid_ids = {c.id for c in candidates}
recommendations = [r for r in parsed if r.restaurant_id in valid_ids]

# EC-L17: fallback
if not recommendations:
    return build_fallback_recommendations(candidates[:5], preferences)
```

**Tests:** `test_parser` — malformed JSON, bad IDs, empty list; mock client for timeout.

---

## 5. Orchestrator (EC-O)

| ID | Edge case | Trigger | Expected behavior | Priority |
|----|-----------|---------|-------------------|----------|
| EC-O01 | Invalid preferences | EC-U* failures | Return validation errors; HTTP 400 equivalent in API; no LLM cost. | P0 |
| EC-O02 | Empty filter result | EC-F01 | Return `RecommendationResponse` with empty list + `empty_reason`; **skip LLM**. | P0 |
| EC-O03 | LLM success but parser yields zero | All IDs invalid | Trigger fallback (EC-L17). | P0 |
| EC-O04 | Concurrent requests | Two users (unlikely MVP) | Stateless orchestrator; each call uses same store snapshot. | P2 |
| EC-O05 | Store not initialized | `get_recommendations` before load | Raise clear `RuntimeError`: *"Restaurant store not loaded."* | P0 |
| EC-O06 | Partial pipeline exception | Bug in filter | Catch; log stack; user message: *"Something went wrong. Try again."* Do not crash UI process. | P0 |
| EC-O07 | Metadata accuracy | Fallback used | `metadata.fallback_used is True`, `candidate_count` matches pre-LLM count. | P0 |
| EC-O08 | Idempotent retry | User retries same search | Same inputs → same filter set; LLM may vary slightly — acceptable for MVP. | P2 |

### Flow decision table

| Validation | Filter | LLM | Outcome |
|------------|--------|-----|---------|
| Fail | — | — | Errors only (EC-O01) |
| Pass | 0 rows | — | Empty state (EC-O02) |
| Pass | ≥1 row | Success + parse OK | Full AI recommendations |
| Pass | ≥1 row | Fail / bad parse | Fallback (EC-L17) |

---

## 6. Presentation / UI (EC-P)

| ID | Edge case | Trigger | Expected behavior | Priority |
|----|-----------|---------|-------------------|----------|
| EC-P01 | Startup while data loading | Large HF download | Show loading screen; disable form until store ready. | P0 |
| EC-P02 | Startup failed (EC-D01) | Ingestion error | Show error page with retry instructions; no broken form. | P0 |
| EC-P03 | Long LLM wait | 10–15s | Spinner/skeleton; disable submit; optional *"Still working…"* after 5s. | P1 |
| EC-P04 | Empty results UI | EC-F01 | Dedicated empty state component with bullet tips (not blank screen). | P0 |
| EC-P05 | Fallback badge | EC-L17 | Subtle banner: *"AI ranking unavailable; showing best matches by rating."* | P1 |
| EC-P06 | Missing optional summary | LLM omits `summary` | Hide summary section; no layout break. | P1 |
| EC-P07 | Very long explanation | 2000-char text | Truncate display with "Read more" expander. | P2 |
| EC-P08 | Cost display missing | `cost` null on restaurant | Show *"Cost not available"* or hide cost line. | P1 |
| EC-P09 | Rating display | `0` or null rating | Show *"No rating"* or omit stars. | P1 |
| EC-P10 | Location dropdown empty | Store failed partially | Disable submit; show error. | P0 |
| EC-P11 | Browser refresh mid-request | User reloads | Harmless; new session; no persisted half-state required. | P2 |
| EC-P12 | Mobile narrow viewport | Small screen | Cards stack vertically; form fields full width. | P2 |

---

## 7. Security & Configuration (EC-S)

| ID | Edge case | Trigger | Expected behavior | Priority |
|----|-----------|---------|-------------------|----------|
| EC-S01 | API key in git | Accidental commit | `.gitignore` `.env`; use `.env.example` only; rotate key if leaked. | P0 |
| EC-S02 | Prompt injection in additional prefs | *"Ignore instructions…"* | System prompt: only rank listed IDs; do not execute user as system; truncate input (EC-U12). | P1 |
| EC-S03 | PII in preferences | User types phone/email | No special storage; do not log full free text in production logs if sensitive. | P2 |
| EC-S04 | `.env` missing | No file on machine | Clear startup message listing required vars. | P0 |
| EC-S05 | Wrong `LLM_MODEL` name | Typo in env | Provider error → fallback path; log model name. | P1 |
| EC-S06 | Hugging Face token required | Private dataset fork | Support optional `HF_TOKEN` in env; document in README. | P2 |

---

## 8. Cross-Cutting & Operational (EC-X)

| ID | Edge case | Trigger | Expected behavior | Priority |
|----|-----------|---------|-------------------|----------|
| EC-X01 | Offline demo | No network at presentation | Ship `data/cache.parquet` or sample JSON; document offline mode. | P1 |
| EC-X02 | Clock skew / SSL errors | Corporate proxy | Document proxy env vars; fail with TLS hint. | P2 |
| EC-X03 | Python version mismatch | Old Python | `requirements.txt` pins minimum version (e.g. 3.10+). | P1 |
| EC-X04 | Disk full on cache write | No space for Parquet | Log warning; run in-memory only without cache. | P2 |
| EC-X05 | Logging sensitive data | Debug logs prompt | Redact API keys; avoid logging full prompts in production. | P1 |
| EC-X06 | Inconsistent cost currency | Dataset mixes formats | Display raw numeric cost with label *"estimated"*; no currency conversion in MVP. | P1 |
| EC-X07 | Fellowship evaluator empty API key | They clone repo without key | README explains mock mode or filter-only demo script. | P1 |
| EC-X08 | Regression after dataset update | HF dataset changed | Version-pin dataset revision in config; ingestion tests catch schema drift. | P1 |

---

## 9. Handling Priority for MVP

### Must implement before demo (P0)

1. EC-D01, D03–D05, D11, D18  
2. EC-U01–U07, U09  
3. EC-F01, F06–F07  
4. EC-L01–L08, L14–L15, L17  
5. EC-O01–O03, O05–O07  
6. EC-P01–P02, P04, P10  
7. EC-S01, S04  
8. EC-F16 (treat input as literal)

### Should implement (P1)

Remaining EC-D06–D10, EC-U08–U13, EC-F04–F05, EC-L09–L13, EC-P03–P05, EC-P08–P09, EC-S02, EC-S05, EC-X01, EC-X07.

### Document or defer (P2)

EC-D09, D16–D17, EC-U14, EC-F11–F14, EC-L19, EC-O04, EC-O08, EC-P07, EC-P11–P12, EC-S03, EC-S06, EC-X02, EC-X04.

---

## 10. Test Case Mapping

| Test file | Edge case IDs |
|-----------|---------------|
| `tests/test_ingestion.py` | EC-D03–D08, D11–D13 |
| `tests/test_filter.py` | EC-F01–F03, F06–F07, F11 |
| `tests/test_parser.py` | EC-L07–L08, L10–L12, L18 |
| `tests/test_orchestrator.py` | EC-O01–O03, O07 |
| Manual UI checklist | EC-P01–P05, EC-F01, EC-L17 |

### Manual QA script (15 min)

1. **Happy path:** Delhi + medium + Italian → ≥1 card with all fields.  
2. **Empty filter:** Delhi + low + obscure cuisine + `min_rating=5` → empty state tips.  
3. **Invalid input:** Submit without location → inline error.  
4. **Fallback:** Invalid API key or mock timeout → list still shown with fallback banner.  
5. **Single result:** Pick niche combo → one card, no crash.  
6. **Grounding:** Verify restaurant names on cards exist in dataset (no invented venues).

---

## 11. User-Facing Message Catalog

| Situation | Message (template) |
|-----------|----------------------|
| Dataset load fail | *Unable to load restaurant data. Check your internet connection or contact support.* |
| Validation — location | *Please select or enter a location.* |
| Validation — budget | *Please select a budget: low, medium, or high.* |
| Validation — rating | *Rating must be between 0 and 5.* |
| Empty filter | *No restaurants match your filters. Try a different cuisine, lower the minimum rating, or change your budget.* |
| LLM fallback | *AI recommendations are temporarily unavailable. Showing top matches based on your filters.* |
| Generic error | *Something went wrong. Please try again.* |
| Truncated candidates (debug) | *Showing top {N} of {M} matches.* |

---

## 12. Traceability

| Source document | Covered by |
|-----------------|------------|
| architecture.md §9 Error matrix | EC-D01, EC-U*, EC-F01, EC-L03–L08 |
| architecture.md §2 Graceful degradation | EC-L17, EC-O03 |
| context.md Success criteria (grounded) | EC-L08, EC-L14 |
| implementation-plan.md Phase 6 | §10 Test mapping, §9 P0 list |

---

## 13. References

- [architecture.md](architecture.md) — §9 Error Handling Matrix  
- [implementation-plan.md](implementation-plan.md) — Phase 6 hardening  
- [context.md](context.md) — Workflow and success criteria  
- Dataset: https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation
