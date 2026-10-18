# QuickIris — scalable consumer-event business roadmap

**Status:** long-term strategy / candidate tracks, not permission to activate every market or monetize before approval. Last discussed 2026-10-18.

## North star
Build a global, multilingual, search-discovered B2C content and consumer-utility portfolio. Start with credible coverage of an upcoming or recently completed event, then offer an interpretation of *why a reader should care / attend / watch / buy*, grounded in verifiable facts, appropriate consumer guidance and regional availability. Build reusable data, localization, informative-graphics, indexing, publication and measurement infrastructure. Ads are the first test, not proof of ultimate monetization.

## Expansion phases and decision gates

### Phase 0 — current validation: NBA + EPL, 8 languages, Blogger + GitHub Pages
- Match previews/recaps + actionable watchpoints; charts from evidence; verified links and translations.
- Backfill priority: completed games in reference past 30 days, future fixture inventory, editorially suitable scheduled previews.
- Build league navigation, job-state/retry, API authorization, analytics and measurement.
- Gate: repeatable search clicks, low verified-error rate, time per 8-language group, value per page, and actual AdSense approval/results (if available).

### Phase 1 — more sports / regions
- Candidate leagues: MLB, NFL, WNBA, NPB/KBO, UEFA competitions, La Liga, Bundesliga, Ligue 1, Serie A, MLS, cricket, tennis, F1, volleyball and local tournaments.
- Select by country-specific search interest, available official schedules/rights, data cost, feasible original explanation, speed-to-publish and incremental revenue/effort.
- Locale != geography: English can serve US/UK/India etc.; Spanish can serve different countries with different ticket/broadcast rights. Avoid naïve duplication per country.
- Preserve 8-language baseline for active selected pieces until the user changes it based on evidence; adding languages/country-specific pages is a separate experiment.

### Phase 2 — non-sports events and promotions
Use the same lifecycle engine with domain-specific fact packs, questions and graphics:
- **Games:** launches, patches, expansions, esports competitions, free-to-play events; answer what changes, when, what device/version and eligibility. Visual: before/after table, timelines.
- **Entertainment:** film/series premieres, concerts, festivals, award shows, live streams; answer when/where, cast/lineup, ticketing/access, schedule changes. Visual: showtime maps/timelines, verified event lineup.
- **Brands / consumer promotions:** seasonal product drops, limited items, promotions, shopping events, new product launches; answer offer conditions, real release dates, region, verified price/availability and expiration. Visual: eligibility decision tree and comparison table. Never invent stock, discounts, coupon codes, paid sponsorship, or urgency.
- **Local public events / travel:** festivals, exhibitions, conventions, community events; answer location, tickets, accessibility, opening dates, transport if verified. Visual: schedule/timezone comparison or sourced map.
- **Tech and app updates:** verified feature rollouts, device compatibility, policy changes. Visual: eligibility/compatibility matrix.
Choose actual niches after measuring search volume, competition, ongoing supply, data sources, rights and editorial effort. Publishing a trend summary without distinctive value is not the strategy.

### Phase 3 — distribution and product businesses
- Repurpose **rights-cleared original** facts and visuals into B2C video/YouTube explainers when evidence supports it; monitor platforms' originality/monetization rules.
- Consider recurring-interest consumer products (web tools, mobile apps, fan/event discovery) only when user behavior supports retention.
- AI-developed games are a separate B2C validation track with gameplay/retention/monetization testing; not assumed automatic extension of the sports site.
- Scale revenue and organization based on actual profit and durable audience, not raw number of AI articles.

## Extensible event model
- `vertical`, `event_type`, `event_id`, `official_source_ids`, `source_license`
- `region_scope`, `audience_country`, `language`, `timezone`, `availability_region`
- `status`: announced / scheduled / rescheduled / live / completed / cancelled / corrected
- `facts_version`, `verified_at`, evidence links and confidence/unknowns
- `article_kind`: preview / guide / recap / update / comparison; each has different editorial rules
- `graphics_dataset_version`, chart type, locale labels
- `publish_owner`, `translation_group`, per-locale URL, state, revision, verification result
- `search_metrics`, `ad_metrics`, measured per locale/vertical/time window

Implementation should use source adapters (NBA/EPL first), a common event-state engine, template/quality modules per vertical, locale/translation modules, chart renderers and publisher adapters for GitHub/Blogger. No event data in a web search snippet alone should be accepted as final.

## SEO & business safeguards
- Search demand is **not** guaranteed clicks; google trends index/volume bands differ from actual search visits.
- A surge that lasts hours may finish before a new site is indexed; prioritize upcoming dates and longer-useful angles.
- Different language URLs, cross-references / hreflang when supported, accurate source/updated time and appropriate locale-specific details.
- Avoid low-value high-volume generation, generic summaries, misinformation, media copyright violations, misleading promotions, unpaid trademark misuse and advertising-policy circumvention.
- Record data provider terms and redistribution/commercial usage before paid automated ingestion.
- Store AdSense/analytics confidentially; aggregate non-private public reports only.

## Expansion decision template
For every new vertical, league, country or language: scope -> official source & license -> last 7/30 days demand evidence -> competition/readership hypothesis -> original editorial angle -> estimated 8-language cost -> compliance/quality gate -> small matched experiment -> search/usage/revenue after defined observation window -> scale/stop decision. Document the dated decision and its evidence.
