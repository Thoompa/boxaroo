# Known issues

Findings from analysing the run logs in `Logs/odyssey/` (47 files, 15 May – 1 Oct 2026, 284 single-category runs, ~737k rows stored, ~515 h of scraping). Only logs were reviewed, never the CSVs, so row-level data quality is unverified. Update status here as items are fixed.

## Background facts

- A "page" is 36 products, but the DOM holds ~72 tiles per page (~2x duplicates). Dedupe in `woolworths_category_data_normaliser.py` hides this, so scraped counts are right but each page does about twice the extraction work needed.
- Woolworths caps a category at 10,000 results (278 pages x 36). Home-lifestyle, cleaning-maintenance, baby, pet, personal-care and beauty all hit it, so "found" cannot tell you whether those are complete.
- Scheduled cadence: Wednesday (~8 categories) and Thursday (~10), one headless process per category.
- Big categories take 4-6 hours each. The latest Wed/Thu batches (30 Sep, 1 Oct) had 7 of 19 categories short or empty.

## Open issues (highest priority first)

1. **Failed runs lose all data and still report success.** *Mostly fixed, see "Fixed" below. Remaining: rows are saved per page, but a failed category is not yet resumed (tickets T2-T6 in the roadmap below: crash-safe checkpoint, in-run retry, cross-run resume).* 46 runs through 1 Oct stored 0 rows after a crash, wasting ~99.5 h; 7-15 Oct added 11 more, including four `tab crashed` on 14 Oct (~11 h each).
2. **Partial categories stored as if complete.** ~25 runs hit the scraper's own "scrape gap" warning. Examples: pantry 1 Oct 2,569/8,268; drinks 572/2,435. Nothing marks the rows as partial.
3. ~~Unreliable expected total ("page data")~~ — fixed, see "Fixed" below.
4. ~~beer-wine-spirits repeats content~~ — cause found and fixed (carousel tiles stored as category rows), see "Fixed". Confirm on the next real run.
5. ~~Badge text parsed as product name~~ — fixed, see "Fixed".
6. **Marketplace (third-party) items.** ~291k incomplete lines are missing only `unit_price`; nearly all are Marketplace sellers (Hoka, Birkenstock, treadmills...) which have no unit price. They make home-lifestyle 88% incomplete and also dominate pet, baby and cleaning. Consider tagging or excluding them.
7. **Per-page counts do not always reconcile.** 15 Jul dinner: pages summed to 158 scraped but the category reported 105. 19 pages where tiles != scraped. Related, from the live pagination tests: results are reshuffled between loads. Reloading page 1 repeats only ~85% of its products and consecutive pages share ~45%, so scraping page by page both duplicates and can miss products.
8. **Runs that vanish.** Dairy 28 Jun, dairy 1 Jul and health-wellness 6 Aug have no summary or stored-rows line (process killed). The 12 Jun FULL run ended in read timeouts; 28 Jun FULL runs failed with `Category '' was not found`.
9. **No retry or resume at run level.** A failed 5-6 h category restarts from scratch.
10. **Chrome stability.** Frequent `tab crashed` in June/July (Chrome 147); mostly replaced by TimeoutExceptions since August.

## Fixed

- **Failed runs lost all data and reported success (issue 1, step 1 of 4).** Root cause: the normaliser caught every exception and returned an empty result, and rows were only written after the whole category finished. Now each page's new rows are appended to the CSV as the page is read (`on_rows` sink, cross-page dedupe), `get_products` returns pages read so far plus an `error` instead of raising (a `TypeError` still propagates as a bug), and each category ends `complete`, `partial` or `failed`. The run summary has a `categories_partial=` field, "Successfully scraped" is only logged for a clean run, `main` exits 1 if anything was partial or failed, and `<csv>.status.json` records state, rows, pages and error per category. `Scripts/run_long_categories.sh` keeps going after a failed category and exits 1 at the end. A scrape gap of 50% or more also marks a category partial. Watch for `Category X PARTIAL/FAILED` and `Pagination aborted` in logs. Re-running a category on the same day still appends to the same CSV (duplicates until resume lands). Regression tests: `Tests/test_run_data_loss_regression.py`.

- **Pagination ended on the first hiccup.** A hung browser mid-advance (120 s read timeout) or a next button not found within 2 s ended the category (`Pagination stop: ...`), causing the 1 Oct partials in beauty, health-wellness, pantry and personal-care. `web_driver.py` now retries on a fresh driver at `?pageNumber=N+1` (up to 3 attempts) and only accepts the end of pagination after a reload. Not yet validated against the live site; watch for `Pagination recovery` warnings in the next batch. Drinks (1 Oct) stopped without any pagination warning, so its cause is unconfirmed.

- **Badge text stored as the product name, was-price glued to the unit price (issue 5).** `ProductParser` now takes the last text line before the action buttons (`Add to cart` / `View similar` / `Save to list`) as the name and skips badge/annotation lines (`BADGE_PATTERN`: `/ 100G`, `...^`, `SUPPLY UPDATE`, `DESIGNS MAY VARY`, `EXTRA n% OFF`, `Sold by`, `Lowest price`, `EST. RESTOCK`, `IN-STORE ONLY`, `EVERYDAY LOW PRICE`, `[unknown]`). The unit price is only the last `$x / unit` on the line (`$3.60 / 100G $29.50 / 1KG` gives `$29.50 / 1KG`). The blacklist now matches whole lines: the old substring match rejected names such as "New Zeland Sauvignon Blanc" because of `new`. The 501 fixture tiles now have 0 bad names and 0 glued unit prices. Layouts of `Lowest price in N days`, `Sold by`, `BONUS CONTAINER CREDIT^` and `EST. RESTOCK` are covered by hand-written tiles only; confirm on the next real run (group names in the CSVs by badge text).
  - **Follow-up: bulleted `Promoted` tag missed by the blacklist.** The 28 Oct run stored `• Promoted` as the name for ~170 rows across seven categories — live tiles render the sponsored tag with a leading bullet, so the whole-line match for `promoted` never hit. `_is_blacklisted` now strips leading bullet/dash characters before matching. Rows scraped before 1 Nov keep the bad `• Promoted` name; recoverable by SKU from a later run.

- **SKU captured.** Each row now ends with a `SKU` column (the Woolworths stockcode). The web driver hands over each tile's link and image URLs and the supermarket's normaliser picks the id (Woolworths: `/shop/productdetails/<stockcode>/...`, image URL as fallback; 40/40 tiles on a live `deli` page, 22 Oct). A tile with no SKU is reported as incomplete (`sku`). CSVs from before this have no SKU column. Stockcodes make issues 4 and 7 measurable (repeats and misses by id) and should show whether Marketplace items (issue 6) use a different id format.

- **Carousel tiles stored as category rows (issue 4).** Cause confirmed on a live `deli` page (25 Oct): 43 tiles in the product grid (`grid-mode_component_grid-collection-container*`), 8 in the "Most Popular" carousel (`horizontal-mode_component_container*`), and a further 20 tiles in another horizontal carousel, all matched by the old `find_elements(TAG, "wc-product-tile")`. `WebDriver._find_product_tiles` now selects only grid tiles (`PRODUCT_GRID_TILE_SELECTOR`) and falls back to every tile with the warning `Product grid not found; collecting every product tile on the page` if the grid markup changes. The category-total tile-count fallback is scoped the same way. Watch for that warning in the next batch. beer-wine-spirits duplicates should fall from 71-79% towards ~50%, measurable by SKU. CSVs from before this fix contain carousel rows (the same few products repeated on every page). Tests use hand-written markup with the live class names; a saved live capture was not kept because the site returned no tiles after repeated loads.

- **Unreliable expected total, "page data" (issue 3, T4).** `get_category_total_items` is unchanged (still returns whatever it parses, including noise from a page that hasn't finished loading), but `WoolworthsCategoryDataNormaliser` no longer trusts it blindly. A new `_sanitize_expected_total` treats anything below `MIN_TRUSTED_TOTAL` (50) the same as a missing total (falls back to `scraped_count`, as before), and exactly `CATEGORY_RESULT_CAP` (10,000) is recorded as a real-but-capped total and excluded from the scrape-gap check, since a capped category's real size is unknown and would otherwise look like a huge false gap. `CategoryData["total_capped"]` carries the flag through to `scrape_coordinator.py` and the status JSON as `expected_total_capped` (additive field, `schema_version` unchanged). `products_found` in the run summary is no longer inflated/distorted by a sub-50 bogus total, since the normaliser already folds it into `scraped_count` before returning. Tradeoff: a category that legitimately has fewer than 50 products will also have its total treated as unknown — acceptable per the known-issues brief, not yet seen in practice. Tests: `Tests/test_woolworths_category_data_normaliser.py` (new cases below "Trustworthy expected total").

## Roadmap: reliable, resumable runs (issues 1, 2, 8, 9)

End state: every page is saved as it is scraped, and a run can read its own checkpoint to continue a half-scraped category. Each ticket should capture more data than the one before it.

- **T1. Incremental save and honest status.** Done (see "Fixed", uncommitted).
- **T2. Page commit protocol and checkpoint file.** Append rows, fsync, then atomically update a checkpoint (`running` state, heartbeat, last committed page, URL). Makes killed runs detectable and a half-written page recoverable (rows already in the CSV count as seen). Build the checkpoint on the `<csv>.status.json` schema (`schema_version` 1).
- **T3. In-run retry and resume.** On a page failure (tile wait timeout, `tab crashed`, `ERR_ADDRESS_UNREACHABLE`), restart the driver at `?pageNumber=N` with a bounded budget. Extends the existing pagination recovery.
- **T4. Trustworthy expected total** (issue 3). Done, see "Fixed" above.
- **T5. Cross-run resume.** Read today's checkpoint, preload seen rows from the CSV, continue at `last_committed_page + 1`. Same calendar day only (results reshuffle); add `--no-resume`.
- **T6. Scheduler retry pass.** `run_long_categories.sh` and the systemd units re-run categories the checkpoints say are incomplete, with a bounded number of passes.
- **T7. Reshuffle tolerance (spike).** Measure how badly page-by-page scraping misses or repeats products (issue 7) and look for a stable ordering.
- **T8. Reporting from checkpoints.** Build the run summary and a `--status` command from checkpoints instead of grepping logs.
- **Refactor (after T2): split `WoolworthsCategoryDataNormaliser`.** It mixes navigation, per-page parse/dedupe/save, outcome judgement, logging and result assembly. Extract (1) a pure `assess_category(total, scraped, error) -> (status, error)` function, (2) a `PageCommitter` class owning `seen_rows`, the sink and the parser call, which is where the T2 checkpoint update belongs, replacing the `remember`/`commit_page` closures, (3) leave a thin scraper, and rename it to match (e.g. `WoolworthsCategoryScraper`). Wait for T2 so the seams are settled; do it before T3-T5 pile more logic in. Leave `_get_products_data`, `ProductParser` and `WebDriver` alone and keep the per-page logging in the scraper. The behavioural tests (`Tests/test_run_data_loss_regression.py` and the normaliser tests) should pass unchanged through the refactor.

## Suggested order

1. Incremental saving plus honest run summary (issues 1, 2, 8).
2. Validate the pagination fix on a real batch; check drinks and beer-wine-spirits (4).
3. ~~Total-count sanity checks (3)~~ — done, see T4.
4. Name-parsing fix (5), then Marketplace handling (6).
5. Optional: skip the duplicate tiles to halve per-page work.
