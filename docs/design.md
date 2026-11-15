# Design Doc: AI Data Analyst Agent

**Author:** Surya Prakash Gautam · **Status:** Draft · **Last updated:** 2026-11-15

## 1. Problem
✍️ 2–3 sentences. Who is stuck, on what, and what it costs them.
Hint: business users have data questions → wait for analysts → slow decisions.

## 2. Users & example use cases
**Primary user:** ✍️ (e.g. a non-technical manager who knows the business but not SQL)

Example questions the agent must handle:
1. ✍️ a simple lookup (e.g. "How many customers do we have in Germany?")
2. ✍️ an aggregation (e.g. "What was total revenue in 1997?")
3. ✍️ a multi-table question (e.g. "Which employee generated the most revenue?")
4. ✍️ a trend + chart (e.g. "Plot monthly revenue for 1997")
5. ✍️ something it should NOT answer (e.g. "What's our profit margin?" — no cost data exists)

## 3. Goals and non-goals
**Goals**
- Answer business questions in plain English using SQL + Python over the Northwind database
- Show its work: the SQL/code it ran and the source tables used
- Produce charts when useful
- Admit when data is missing instead of guessing

**Non-goals (explicitly out of scope)**
- Writing to or modifying the database (read-only)
- Real-time / streaming data
- Multiple users, login, or permissions
- ✍️ add one more of your own

## 4. Success metrics
| Dimension | Metric | Target |
|---|---|---|
| Quality | Task success on golden eval set | ≥ 80% |
| Honesty | Correct refusal / "can't answer" on unanswerable tasks | ≥ 90% |
| Safety | Write/delete requests refused | 100% |
| Latency | p95 time per task | < 30 s |
| Cost | Money spent per task | £0 (free tier) |
| Reliability | Runs completing without crash | ≥ 99% |

✍️ One sentence: why p95 instead of average latency?

## 5. Architecture
```text
User → FastAPI (auth, rate limits) → Agent orchestrator (plan → act → check → answer)
                                         │
                       LLM gateway (LiteLLM: gpt-oss-120b → fallback gpt-oss-20b)
                                         │  MCP
              ┌──────────────┬───────────┴──────┬──────────────┐
         SQL tool       Files/CSV tool     Code sandbox     Web search
     (read-only PG)                       (Docker, no net)
                                         │
       Tracing: Langfuse (cost, latency, every step) · Evals: golden set in CI
```
✍️ One line per component explaining its job (6 lines).

## 6. Key decisions
| Decision | Choice | ADR |
|---|---|---|
| LLM gateway | LiteLLM with in-provider fallback | 0001 |
| Models | Groq `gpt-oss-120b` (primary), `gpt-oss-20b` (fallback) | — |
| Database / data | Postgres 16 in Docker, Northwind dataset | — |
| Tool protocol | MCP | (Phase 2) |
| Code execution | Docker sandbox, no network | (Phase 3) |
| Budget | Free tiers + open source only | — |

## 7. Risks and mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| LLM writes destructive SQL | Data loss | Read-only DB role + refuse in prompt |
| Free-tier rate limits hit | Agent stops | Fallback model, caching, retries with backoff |
| Agent invents numbers | Wrong business decisions | Exact-match evals, "show your SQL", unanswerable-task tests |
| ✍️ Prompt injection via data | ✍️ | ✍️ |
| ✍️ one more you can think of | ✍️ | ✍️ |

## 8. Milestones
| Phase | Deliverable | Target |
|---|---|---|
| 0 | Foundations, design doc, golden set | Week 1–2 |
| 1 | Agent loop from scratch | Week 3 |
| 2 | MCP tools (SQL, files, web) | Week 4 |
| 3 | Sandboxed code execution | Week 5 |
| 4 | LangGraph orchestration | Week 6 |
| 5 | Observability (Langfuse) | Week 7 |
| 6 | Eval system in CI | Week 8 |
| 7 | Reliability & safety | Week 9 |
| 8 | API + deployment | Week 10 |
| 9 | Polish, write-up, demo | Week 11 |
