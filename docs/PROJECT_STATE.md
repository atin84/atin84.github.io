# QuickIris — durable current state / resume checkpoint

**State last reconciled:** 2026-10-18 KST, based on repository reads; operational actions not revalidated in the browser in this update. **Always inspect live main / CI / Blogger before executing.** This file is a handoff checkpoint, not an automatic status monitor.

## Verified from repository in current reconciliation
- Repository: https://github.com/atin84/atin84.github.io (public); sites: https://atin84.github.io and https://quickiris.blogspot.com.
- Main at inspection: `1b4b8d67777e9ded8c65598d0e0badb96d54239b` (commit message: **Add multilingual NBA and Premier League categories**). This commit modified `build.py`, `assets/style.css` and `tests/test_build.py`.
- Prior publication record `experiment/sports-test-2026-10-17-publication.json` and README report **32 published and visually checked sports language pages** (4 article groups × 8 languages; 16 each Blogger/GitHub). This reconciliation did not re-open every remote page, so check live URLs before re-publishing.
- GitHub NBA/EPL multilingual category generator was committed; live category navigation and latest CI status must be checked. **Blogger labels/category navigation are NOT verified as complete**.
- The 2026-10-18 request to backfill past one month of NBA/EPL completed matches and inventory all future scheduled matches remains **unverified / not marked completed**. Do not infer zero work; inspect latest code, commits, posts and any available task records for partial work first.
- Full hourly discovery -> facts -> article -> graphic -> all 8 translations -> publish/update is NOT deployed as an autonomous pipeline. Blogger OAuth publishing and persistent status tracking have not been confirmed as connected.
- AdSense applications were submitted previously; approval/current advertising must be freshly checked (do not infer approval).

## Active GitHub Issues
- [#1 NBA/EPL categories and Blogger labels](https://github.com/atin84/atin84.github.io/issues/1)
- [#2 Historical completed-fixture inventory](https://github.com/atin84/atin84.github.io/issues/2)
- [#3 Future scheduled-fixture inventory](https://github.com/atin84/atin84.github.io/issues/3)
- [#4 Eight-language batch publisher and hourly monitor](https://github.com/atin84/atin84.github.io/issues/4)

## Active milestone sequence (small resumable units)
- [ ] **M1: Category navigation audit** — verify GitHub NBA/EPL category listings deployed and correct across languages; inspect Blogger NBA/EPL labels and menu; add/fix missing Blogger category links and classify earlier posts. Save screenshots/URLs & test result.
- [ ] **M2: Historical match inventory** — as-of date 2026-10-18, compile all officially completed EPL league and NBA competition-specific matches from 2026-09-18 to 2026-10-18 inclusive; preserve IDs, dates, statuses, source URL, category (NBA preseason versus regular season). Count before publication.
- [ ] **M3: Future fixture inventory** — inventory officially listed NBA/EPL future fixtures as of 2026-10-18, recording publication-relevant changes. Do NOT publish the entire remote future season as empty SEO previews; select useful pregame angles.
- [ ] **M4: Batch publication** — for validated previously uncovered games, select a bounded batch (e.g. 2-5 match/article groups) with 8 languages each, data graphics, human factual/editorial review, no duplicated URL; publish and verify. Commit progress.
- [ ] **M5: Hourly workflow prototype** — event change detector, durable state, retry/compensation, source/rights rules, eight-locale pipeline, Blogger OAuth/patch, GitHub deployment, analytics. Run once end-to-end before scheduling.

## Definition of done for a batch
(1) stable league+season+match_id and article kind, (2) official/rights-compatible evidence + checked timestamps, (3) original readable editorial value, (4) accurate data visualization, (5) each of eight URLs returns correct language/content, (6) links and metadata checked, (7) publisher URL and revision saved, (8) build/test result, (9) this file and relevant GitHub Issue updated.

## Last known commands
`python3 -m unittest discover -s tests -v`
`python3 build.py --config config.json --content content --out dist`

## Resume record template (append or replace this block after each verified batch)
- Checked at (UTC):
- Main SHA / commit:
- Issue / batch IDs:
- Before state:
- Changes made:
- Validation/test outcomes:
- Published URLs / count:
- Failures and uncertain remote writes:
- Next smallest task:
- Blocking auth, policy or paid-source requirement:
- Next agent should read:

## Privacy
This file is PUBLIC. Never write tokens, secrets, API keys, sensitive personal context, unpublished business financial details or raw private AdSense reports here. Keep authenticated operational state and private analytics in a private storage/secret manager.
