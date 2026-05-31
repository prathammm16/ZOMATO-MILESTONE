# Project Context: AI-Powered Restaurant Recommendation System

> Source: [Docs/problemStatement.txt](Docs/problemStatement.txt) — Zomato-inspired use case for the Project Manager Fellowship milestone.

## Overview

Build an **AI-powered restaurant recommendation service** inspired by Zomato. The system combines **structured restaurant data** with a **Large Language Model (LLM)** to suggest restaurants that match user preferences and explain why each option fits.

## Objective

Design and implement an application that:

1. Accepts user preferences (location, budget, cuisine, ratings, and more)
2. Uses a real-world restaurant dataset
3. Uses an LLM to produce personalized, human-like recommendations
4. Displays clear, useful results to the user

## Dataset

| Item | Detail |
|------|--------|
| **Source** | Hugging Face |
| **URL** | https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation |
| **Usage** | Load, preprocess, and extract fields for filtering and LLM prompts |

**Relevant fields to extract** (non-exhaustive):

- Restaurant name
- Location
- Cuisine
- Cost
- Rating
- Other fields as needed for filtering and display

## System Workflow

### 1. Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face
- Extract structured fields (name, location, cuisine, cost, rating, etc.)

### 2. User Input

Collect preferences including:

| Preference | Examples / notes |
|------------|------------------|
| **Location** | Delhi, Bangalore |
| **Budget** | low, medium, high |
| **Cuisine** | Italian, Chinese |
| **Minimum rating** | Numeric threshold |
| **Additional** | family-friendly, quick service, etc. |

### 3. Integration Layer

- Filter and prepare restaurant records that match user input
- Pass structured candidate results into an LLM prompt
- Design prompts so the LLM can **reason** and **rank** options

### 4. Recommendation Engine (LLM)

The LLM should:

- **Rank** restaurants
- **Explain** why each recommendation fits the user’s preferences
- **Optionally** summarize the overall set of choices

### 5. Output Display

Present top recommendations in a user-friendly format. Each item should include:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation (why it was recommended)

## Architecture (Logical)

```
[Hugging Face Dataset] → [Preprocess / Extract fields]
                              ↓
[User preferences] → [Filter & prepare candidates] → [LLM prompt]
                              ↓
                    [Rank + explain + optional summary]
                              ↓
                    [Formatted results UI / output]
```

## Success Criteria (Implicit)

- End-to-end flow: ingest data → collect preferences → filter → LLM → display
- Recommendations are grounded in dataset fields, not purely hallucinated listings
- Explanations are personalized and tied to stated preferences
- Output is readable and actionable for a end user

## Out of Scope (Not Specified in Problem Statement)

The problem statement does not mandate:

- Specific tech stack (Python, web framework, API provider)
- Deployment target
- Authentication or user accounts
- Persistence of search history

These can be chosen during implementation unless fellowship requirements add constraints elsewhere.

## Key Links

- **Problem statement file:** `Docs/problemStatement.txt`
- **Dataset:** https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation

## Glossary

| Term | Meaning in this project |
|------|-------------------------|
| **Integration layer** | Code that filters data by user input and formats context for the LLM |
| **Recommendation engine** | LLM-driven ranking and explanation step |
| **Budget tiers** | low / medium / high — map to cost fields in the dataset during filtering |
