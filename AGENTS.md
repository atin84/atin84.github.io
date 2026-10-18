# QuickIris — repository agent instructions

This file is the stable entry point for coding agents (including Codex). For session continuity read **docs/PROJECT_STATE.md** first, then **docs/HANDOFF.md**, **docs/EXPANSION_ROADMAP.md**, **experiment/protocol.md**, and **experiment/editorial-guidelines.md** as needed.

## Mission and scope
- Build a search-driven, multilingual B2C publishing system with reliable reporting and the ability to extend from sports to other time-sensitive events.
- Active launch verticals: NBA and English Premier League (EPL). Every *selected* article is prepared in 8 languages: en, ko, es, ja, pt-BR, fr, de, hi.
- Two live test publishers: GitHub Pages and Blogger. Keep matching leagues/languages on both, without duplicating the same match+article_kind+language across sites.
- Story value: before an event, explain why it matters and what to watch; afterwards, explain what happened and why it mattered. Graphics must communicate verified data, never decorative pseudo-analysis.
- Long-term B2C expansion: other sports; game launches/patches; entertainment premieres; brand promotions/limited releases; public festivals and events. Expansion is gated by evidence and source/data permissions.

## Work protocol — CRITICAL for interrupted sessions
1. Read docs/PROJECT_STATE.md and inspect live GitHub main, latest commits/CI, existing content and publication registry **before any edits or bulk writes**.
2. Identify the first unfinished verified milestone. Do not treat a plan as implemented, nor rerun a completed or uncertain publish.
3. Plan a **small resumable batch**, not a one-shot entire season. Build/validate; publish; verify actual URLs; update durable state and issue; then proceed.
4. Use GitHub Issues for open tasks and acceptance criteria. Track in-progress/backfill jobs with stable IDs and statuses: discovered -> validated -> drafted -> reviewed -> published -> verified, plus blocked/uncertain.
5. After every successful batch or material decision, update docs/PROJECT_STATE.md (what changed, commit, URL, next task, blockers, verification time).
6. If a job fails, report the exact completed and uncertain work; do **not** quietly start again or promise background completion.
7. Never place API keys, OAuth tokens, private analytics, personal finances, or unpublished privileged material in this **public** repository.

## Quality / compliance
- Every match, result, date, lineup, player claim and chart datum requires traceable official or properly licensed sources and a recorded as-of time.
- Differentiate NBA preseason/regular season/postseason; verify official final state; differentiate EPL league fixtures from other competitions.
- No fabricated match events, athlete quotes or causal claims. Do not spin duplicate, thin SEO pages; no invented urgency, inventory or ticket availability.
- For multilingual pages, localize terminology, preserve facts, link translations, and regenerate translations/graphics if shared factual data changes.
- Copyright and commercial-use rights matter for sports APIs, videos, player photos and logos. Use original data diagrams / licensed assets.
- Consult current Google Search / AdSense guidance before scaling. Never label AI-only checking as human review.

## Verify
- Python 3.10+: `python3 -m unittest discover -s tests -v`; `python3 build.py --config config.json --content content --out dist`.
- Confirm correct headline/language, graphic, source links, translation navigation, canonical/hreflang as applicable, and real public URL.
- The scheduled GitHub workflow rebuilds approved source content; it is **not** a working hourly AI editorial engine. Blogger API OAuth/scheduled auto-posting remains unverified until tested.

## Resume
For an interrupted task say: "Resume QuickIris from docs/PROJECT_STATE.md and linked GitHub Issues. Verify main and published URLs first; complete one small batch, record state, and stop at a clear checkpoint."
