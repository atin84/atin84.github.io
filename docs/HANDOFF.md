# QuickIris — cross-chat / cross-model handoff

**Last strategy consolidation:** 2026-10-18 (KST). **Operational truth:** see [PROJECT_STATE.md](PROJECT_STATE.md) and latest GitHub commits / live publisher URLs. This document is a strategy snapshot, not proof of newly completed execution.

## Product and business
QuickIris is a search-first, multilingual B2C editorial system. Start with precise, entertaining and accessible sports match previews / recaps; expand to other sports and later time-sensitive consumer events. Monetization begins with Google AdSense once each publishing site is approved; later optional YouTube/video, consumer apps and games are independent experiments. Do not confuse generating many pages with capturing search traffic or profit. Avoid B2B sales/service businesses.

**Quality differentiation:** teach a first-time watcher where to look and help enthusiasts understand match meaning; before-match watchpoints and after-match verified answers must connect. Original, sourced data diagrams (match flow, points-by-period, event timeline, comparative metrics, relevant team/player relations) are preferred over decorative AI illustrations. Truth, usefulness, natural localization and editorial judgment precede volume.

## Confirmed decisions
- **Initial leagues:** NBA and England's Premier League (EPL), both active from the start. Do not mix EPL with FA Cup or NBA regular-season with preseason.
- **All selected articles in 8 languages:** English (en), Korean (ko), Spanish (es), Japanese (ja), Brazilian Portuguese (pt-BR), French (fr), German (de), Hindi (hi). English is reference editorial language; 7 localizations derive from verified shared facts. Separate language URLs and clear localization.
- **Two channels to compare:** GitHub Pages https://atin84.github.io and Blogger https://quickiris.blogspot.com. Allocate different but comparable matches from each league to the two channels, and keep each match's translations/updates on one owner channel. Avoid duplicate same-intent pages across platforms.
- **Flexible publishing frequency:** hourly **detection** is a target, NOT a requirement to post hourly. Publish or update only on a verified meaningful change.
- **Writing:** pre-match why watch / tactical or player watchpoints / relevant historical story / viewing conditions; post-match official result / major turning points / verified explanations / next match meaning. Label speculation and limitations; keep beginner-friendly explanations without diluting expert value.
- **Information graphics:** NBA comparison or scored-points flow; EPL comparison or verified incident timeline; facts/labels synchronized across all eight languages.
- **Measurement:** search impressions, clicks, CTR, time-to-index, actual region and language, page RPM once ads live, cost, errors, completeness and return readership. Compare matched cohorts; impressions alone are not revenue.

## Current and next tasks
See [PROJECT_STATE.md](PROJECT_STATE.md). Latest known: 4 story groups × 8 locales = 32 published public sports posts (16 per platform). GitHub multilingual NBA/EPL **category support was committed on 2026-10-18**; actual UI/deployment needs confirmation. Blogger category labels and menu require separate verification. The previous chat was interrupted before bulk backfill.

**Backfill user request, bounded reference time 2026-10-18:**
1. Collect official *completed* NBA and EPL fixtures roughly 2026-09-18 through 2026-10-18, with all competition/status distinctions; no phantom games.
2. Collect NBA and EPL officially scheduled future fixtures as of that date. This is a **fixture inventory**, not permission to publish hundreds of stale or low-value previews at once.
3. Deduplicate using league+season+official match ID, and record data provenance.
4. Build researched match/article units; produce all eight locales and a relevant factual chart; publish in small batches and verify URLs. Update pre-existing previews now obsolete before publishing a duplicate.
5. Track the actual remaining number of unprocessed matches and tasks; never trust a claim that a previous interrupted batch failed/succeeded without checking remote state.

## Operating model and responsibilities
Change detection (hourly scheduling desired) -> candidate/priority -> official & licensed data -> evidence package -> natural editorial article -> data-derived chart -> eight-language editing -> accuracy/content review -> publish/patch -> verify/index/analytics. Store states and article IDs durably; retry only failed steps. The existing GitHub re-build timer is NOT an autonomous news-writing agent; Blogger OAuth + durable job journal + posting/patching automation were not connected in the last confirmed status. Do not claim autonomous end-to-end execution.

## Expansion beyond sports
Full phased plan: [EXPANSION_ROADMAP.md](EXPANSION_ROADMAP.md). The common product abstraction is **event/consumer-interest entity + locale + lifecycle + evidence + article kind + publication state**. Expand to international leagues, concerts/streaming and game launches, brand promotion/seasonal limited editions, ticketed events/festivals, consumer product launches. These are *candidates*, never automatically enabled until demand, licensing, edit quality and economics justify each vertical.

## Where to resume
- First read [PROJECT_STATE.md](PROJECT_STATE.md), latest main commit, relevant GitHub Issues and publication record `experiment/sports-test-2026-10-17-publication.json`.
- Verify remote published pages, code and CI **before** editing or bulk publishing.
- Continue one small checkpointed unit. Commit and update state/Issues.
- Never put credentials, AdSense identifiers, private analytics or personal financial details in public GitHub.
