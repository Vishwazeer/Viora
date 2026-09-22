# EVAL — Viora

> **Evaluation Date:** 2026-05-29
> **Evaluator:** Automated Portfolio Review
> **Maturity Level:** Production-Ready

---

## 1. Project Purpose & Problem Statement

Viora is a production-grade inbound AI voice receptionist for Indian healthcare clinics, specifically designed for the "last-mile" problem of clinic telephony: the majority of small-to-mid-size clinics in India cannot afford a full-time receptionist yet handle a high volume of patient calls for appointment booking, lab status inquiries, and symptom queries. Viora handles all of this end-to-end — in English, Hindi, and Marathi — with native code-switching support (Hinglish).

The system targets a real market: millions of small clinics across India lack automated intake solutions, and the existing options (IVR trees, offshore call centers) have terrible patient experience. Viora addresses the latency, language, and compliance (India's DPDP Act) dimensions simultaneously, which is a genuinely hard multi-constraint problem.

---

## 2. Technical Architecture

Viora is a multi-component real-time voice pipeline with the following layers:

**Telephony Layer**: Exotel SIP trunking handles Indian PSTN connectivity, feeding audio into **LiveKit Cloud** (WebRTC) which bridges telephone audio to the Python agent.

**Agent Pipeline**: A LiveKit Agents Python worker orchestrates:
- **STT**: Sarvam AI (Indian-language-optimized speech-to-text) — covers en-IN, hi-IN, mr-IN
- **LLM**: Initially Gemini, migrated to **Groq** (`llama-3.1-8b-instant`) for sub-100ms latency
- **TTS**: Sarvam AI with language-specific voice personas (Meera/Pavithra/Arvind)
- **Tool Calls**: 5 HMS tools (clinic info, doctor roster, availability, book, cancel) wired directly into the LLM's function-calling API

**Backend**: FastAPI + SQLAlchemy ORM, persisting to **Supabase PostgreSQL** (cloud-hosted). Handles call logs, transcripts, DPDP consent ledger, appointments, and audit events.

**Dashboard**: React 18 (Vite) admin UI exposing live call monitoring, transcript viewer, escalation queue, appointments & SMS demo page, and system health indicators.

**DPDP Compliance**: Spoken consent captured at call start; audit_events table is append-only (never updated/deleted); 7-day audio retention; 365-day transcript retention; full data erasure on request.

The journey.md documents a key architectural evolution: the latency breakthrough came from swapping the LLM provider from native Gemini (2-3s) to Groq LPUs (sub-100ms), which was critical for barge-in and natural conversation flow.

---

## 3. Model/Algorithm Details

Viora does not train custom models. It leverages:
- **Sarvam AI STT** — purpose-built for Indian language phonetics, significantly outperforming Whisper on Hindi/Marathi clinical vocabulary
- **Groq Llama-3.1-8b-instant** — ultra-low latency inference, the key unlock for real-time voice
- **Sarvam TTS (Bulbul v2)** — the system prompt engineering enforces 1-3 sentence responses to minimize TTS latency
- **Emergency detection**: Rule-based keyword matching across all 3 languages triggers immediate escalation (call transfer + 108/112 advisory) — this is appropriately a deterministic system, not ML, for safety-critical paths

---

## 4. Strengths

- **Real production architecture** — LiveKit + Exotel + Supabase is a legitimate deployed stack, not a simulation.
- **Multilingual code-switching** — handling Hinglish natively is a genuine technical challenge addressed correctly.
- **DPDP Act compliance** — most projects ignore data compliance entirely; Viora has spoken consent, immutable audit logs, and configurable retention policies.
- **Sub-100ms voice pipeline** — the LLM provider migration to Groq shows real performance engineering judgment.
- **HMS-agnostic adapter interface** — the mock vs. Eka Care HMS adapter pattern makes the system portable across EHR vendors.
- **Demo mode** — full system runs without any API keys, making the portfolio immediately accessible.
- **CI/CD pipeline** — GitHub Actions achieves a clean build + lint (Ruff, ESLint, Bandit security scan).
- **Test suite** — pytest with coverage reporting exists; the journey.md documents the CI refactor journey in detail.
- **Cost modeling** — explicit per-minute and per-month cost projections are included, demonstrating production thinking.

---

## 5. Limitations & Known Gaps

- **Exotel integration is aspirational** — actual SIP trunking requires a paid Exotel account; in practice the portfolio demo will run in LiveKit's browser room, not as a real phone call.
- **Supabase dependency** — cloud DB introduces latency for each tool call (appointment booking hits Supabase); a local SQLite fallback would be safer for demos.
- **No speaker diarization** — multi-speaker scenarios (patient + family member on call) are not handled.
- **Symptom triage is heuristic** — the journey mentions ICMR-aligned risk scoring but no actual ICMR model integration is described; it appears to be rule-based keyword detection.
- **Single-agent, no escalation queue logic** — the admin dashboard shows an escalation queue, but the transfer mechanism depends on Exotel capabilities not available in demo mode.
- **Marathi coverage** — while listed as supported, Marathi clinical vocabulary in Sarvam's model may be sparser than Hindi; this is not benchmarked.

---

## 6. Code Quality Assessment

**Structure**: Well-organized module hierarchy — `agent/core/`, `agent/hms/`, `agent/tools/`, `agent/prompts/`, `api/routes/`, `api/middleware/`, `db/`. Separation of concerns is clear and professionally executed.

**Documentation**: README is comprehensive. `journey.md` is exceptional — it reads as a genuine engineering log with specific bug diagnoses, architectural decisions, and production cost estimates. `agent_help.txt` (30KB) and `session_help.txt` (44KB) suggest extensive inline documentation or prompt engineering documentation.

**Tests**: `pytest` suite exists in `tests/`, with `pytest.ini` and coverage reporting configured. Ruff is configured via `pyproject.toml`.

**CI/CD**: GitHub Actions runs Ruff, ESLint, and Bandit. The journey.md documents achieving a "green tick" across all checks.

**Docker**: Full `docker-compose.yml` + `Dockerfile` for container deployment. Legitimate production containerization.

**Security**: Bandit scan passed; `0.0.0.0` binding explicitly marked `# nosec B104`; DPDP compliance architecture is thoughtful.

---

## 7. Maturity Breakdown

| Dimension | Score | Notes |
|-----------|-------|-------|
| Functionality | 9/10 | Full voice pipeline; demo mode makes it instantly accessible |
| Code Quality | 8/10 | Clean structure, linting, security scan; test coverage depth unclear |
| Documentation | 9/10 | README + journey.md + extensive help files = exceptional |
| Scalability | 7/10 | Supabase scales; LiveKit Cloud scales; single agent worker is the bottleneck |
| Security | 8/10 | DPDP compliance, Bandit scan, audit logs; auth layer not described |
| **Overall** | **8.2/10** | Most production-realistic project in the portfolio |

---

## 8. Suggested Next Steps

1. **Add WebRTC browser-room demo flow** — since Exotel requires a paid account, build a browser-to-agent demo path via LiveKit's JS SDK so evaluators can actually talk to Viora from a laptop without a phone.
2. **Benchmark Marathi STT accuracy** — run a test set of clinical phrases through Sarvam vs. Whisper in Marathi to validate the claim; the results would be a compelling data story.
3. **Replace Supabase with a local SQLite fallback** — for portfolio demos, adding `USE_LOCAL_DB=true` mode with SQLite would eliminate the cloud dependency and make demos fully self-contained.

---

## 9. Verdict

Viora is the most architecturally ambitious and production-realistic project in this portfolio. It tackles a genuine market problem (Indian clinic telephony) with a well-chosen stack (LiveKit, Groq, Sarvam AI), demonstrates real performance engineering (LLM provider migration for latency), and shows regulatory awareness (DPDP compliance) that is rare in portfolio projects. The journey.md is particularly impressive as evidence of how the system was debugged and evolved. The main caveat is that full functionality depends on paid external services (Exotel, Sarvam, LiveKit Cloud), making end-to-end validation for evaluators dependent on demo mode — but the demo mode implementation is thoughtful.

---
<p align="center">Made by Viora Health Technologies</p>

