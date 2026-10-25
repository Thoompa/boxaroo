# Boxaroo Jira ticket drafts

Source: `.claude/known-issues.md`. Issues 1, 8 and 9 are covered by the resume tickets (R2-R5), so they have no tickets of their own. Order within each section is priority order. "Blocked by" uses the ticket keys below.

## Epic E1: Reliable, resumable runs

Every page is saved as it is scraped, and a run can read its own checkpoint to continue a half-scraped category.

### R1. Trustworthy expected total
- **Type:** Bug | **Priority:** High | **Covers:** issue 3 (roadmap T4)
- **Problem:** `get_category_total_items` often returns 10-20 or 0 when the page has not finished loading. Exactly 10,000 is Woolworths' result cap, not a count.
- **Scope:** Ignore values below ~50 and retry the read. Treat exactly 10,000 as a cap. Record `expected_total` and a `capped` flag in `<csv>.status.json`.
- **Acceptance criteria:**
  - A total below 50 is never used for completeness checks.
  - A 10,000 total sets `capped: true` and is not compared against rows scraped.
  - Unit tests cover 0, 10, 49, 50, 9,999 and 10,000.
- **Blocks:** R4, R5, D1

### R2. Page commit protocol and checkpoint file
- **Type:** Story | **Priority:** High | **Covers:** roadmap T2
- **Scope:** Append rows, fsync, then atomically update a checkpoint (`running` state, heartbeat, last committed page, URL). Build on the `<csv>.status.json` schema (`schema_version` 1).
- **Acceptance criteria:**
  - A killed run leaves a checkpoint in `running` state with a stale heartbeat.
  - Rows already in the CSV count as seen after a crash mid-page.
  - Regression tests cover a kill between append and checkpoint update.
- **Blocks:** R3, R4, R6, T8-refactor

### R3. In-run retry and resume
- **Type:** Story | **Priority:** High | **Covers:** issue 9, roadmap T3
- **Scope:** On a page failure (tile wait timeout, `tab crashed`, `ERR_ADDRESS_UNREACHABLE`), restart the driver at `?pageNumber=N` with a bounded budget. Extends the existing pagination recovery.
- **Acceptance criteria:** A simulated failure on page N resumes at N and the category completes. Exhausting the budget ends the category `partial` with the error recorded.
- **Blocked by:** R2

### R4. Cross-run resume
- **Type:** Story | **Priority:** High | **Covers:** issues 1, 8, 9, roadmap T5
- **Scope:** Read today's checkpoint, preload seen rows from the CSV and continue at `last_committed_page + 1`. Same calendar day only, because results reshuffle. Add `--no-resume`. Removes the duplicate rows from same-day re-runs.
- **Acceptance criteria:** Re-running a half-scraped category the same day adds no duplicates. A next-day run starts fresh. `--no-resume` forces a fresh run.
- **Blocked by:** R1, R2

### R5. Scheduler retry pass
- **Type:** Story | **Priority:** Medium | **Covers:** roadmap T6
- **Scope:** `Scripts/run_long_categories.sh` and the `Deploy/` systemd units re-run categories the checkpoints say are incomplete, with a bounded number of passes.
- **Blocked by:** R4

### R6. Report from checkpoints and add `--status`
- **Type:** Story | **Priority:** Medium | **Covers:** roadmap T8
- **Scope:** Build the run summary and a `--status` command from checkpoints instead of grepping logs.
- **Blocked by:** R2

### R7. Split `WoolworthsCategoryDataNormaliser`
- **Type:** Tech debt | **Priority:** Medium
- **Scope:** Extract (1) a pure `assess_category(total, scraped, error) -> (status, error)`, (2) a `PageCommitter` owning `seen_rows`, the sink and the parser call, (3) a thin scraper renamed to match (e.g. `WoolworthsCategoryScraper`). Leave `_get_products_data`, `ProductParser` and `WebDriver` alone.
- **Acceptance criteria:** `Tests/test_run_data_loss_regression.py` and the normaliser tests pass unchanged.
- **Blocked by:** R2. Do before R3-R5.

## Data quality

### D1. Make partial status visible to readers of the data
- **Type:** Story | **Priority:** High | **Covers:** issue 2
- **Problem:** Partial categories are marked only in `<csv>.status.json`. The CSV and `BoxarooApp/` still treat a partial category (e.g. pantry 2,569 of 8,268) as complete.
- **Scope:** Have the viewer read the status file and badge partial/failed categories. Add a `capped` state for 10,000-result categories. Tighten the 50% gap threshold (value to be agreed). Do not backfill old CSVs; note in `known-issues.md` that data from before the status file is unverified.
- **Acceptance criteria:** A partial category is visibly flagged in the viewer. Capped categories are not reported as complete or partial.
- **Blocked by:** R1

### D2. Collect only tiles from the product grid
- **Type:** Bug | **Priority:** High | **Covers:** issue 4
- **Problem:** `get_products` collects every `wc-product-tile`, including the 8-tile "Most Popular" carousel (`horizontal-mode_component_*`), so unrelated repeating products are stored as category rows on every page. Beer-wine-spirits is 71-79% duplicates.
- **Scope:** Restrict collection to `grid-mode_component_*`. Re-measure duplicates by SKU.
- **Acceptance criteria:** Carousel tiles never appear in output. The live fixture shows 44 grid tiles and 0 carousel tiles collected.

### D3. Tag or exclude Marketplace items
- **Type:** Story | **Priority:** Medium | **Covers:** issue 6
- **Problem:** About 291k incomplete lines are missing only `unit_price`, nearly all third-party Marketplace sellers. They make home-lifestyle 88% incomplete and also dominate pet, baby and cleaning.
- **Scope:** Detect Marketplace items (use SKU format as a signal once real runs exist), then tag them in a column or exclude them. Decide which with the viewer in mind.

### D4. Reshuffle tolerance spike
- **Type:** Spike | **Priority:** Medium | **Covers:** issue 7, roadmap T7
- **Problem:** Results reshuffle between loads. Reloading page 1 repeats ~85% of its products and consecutive pages share ~45%. Per-page counts do not always reconcile (15 Jul dinner: 158 scraped versus 105 reported).
- **Scope:** Use SKUs to measure how many products page-by-page scraping misses or repeats, and look for a stable ordering. Output is a written finding with a recommendation.

### D5. Skip duplicate tiles to halve per-page work
- **Type:** Improvement | **Priority:** Low
- **Problem:** The DOM holds ~72 tiles per 36-product page. Dedupe hides the duplicates but extraction still does about twice the work.

## Validation and stability

### V1. Validate pagination recovery on a real batch
- **Type:** Task | **Priority:** High
- **Scope:** Run a Wednesday/Thursday batch and watch for `Pagination recovery` warnings. Check that the 1 Oct partials (beauty, health-wellness, pantry, personal-care) no longer stop early.
- **Related:** drinks on 1 Oct stopped with no pagination warning. Find the cause.

### V2. Confirm badge-parsing layouts on a real run
- **Type:** Task | **Priority:** Low
- **Scope:** `Lowest price in N days`, `Sold by`, `BONUS CONTAINER CREDIT^` and `EST. RESTOCK` are covered only by hand-written tiles. Group names in the new CSVs by badge text and confirm none leak through.

### V3. Chrome stability
- **Type:** Investigation | **Priority:** Low | **Covers:** issue 10
- **Scope:** `tab crashed` was frequent in June and July on Chrome 147, and has mostly become TimeoutExceptions since August. Track the rate after R3 lands and decide whether further work is needed.

## Housekeeping

### H1. Refresh `known-issues.md`
- **Type:** Task | **Priority:** Low
- **Scope:** The "Fixed (uncommitted)" heading is stale, because the badge and SKU fixes merged in PRs #33 and #34. Confirm which other fixes landed and update the statuses.
