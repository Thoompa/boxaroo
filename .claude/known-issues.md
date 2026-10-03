# Known issues

Findings from analysing the run logs in `Logs/odyssey/` (47 files, 15 May – 1 Oct 2026, 284 single-category runs, ~737k rows stored, ~515 h of scraping). Only logs were reviewed, never the CSVs, so row-level data quality is unverified. Update status here as items are fixed.

## Background facts

- A "page" is 36 products, but the DOM holds ~72 tiles per page (~2x duplicates). Dedupe in `woolworths_category_data_normaliser.py` hides this, so scraped counts are right but each page does about twice the extraction work needed.
- Woolworths caps a category at 10,000 results (278 pages x 36). Home-lifestyle, cleaning-maintenance, baby, pet, personal-care and beauty all hit it, so "found" cannot tell you whether those are complete.
- Scheduled cadence: Wednesday (~8 categories) and Thursday (~10), one headless process per category.
- Big categories take 4-6 hours each. The latest Wed/Thu batches (30 Sep, 1 Oct) had 7 of 19 categories short or empty.

## Open issues (highest priority first)

1. **Failed runs lose all data and still report success.** Rows are only written at the end of a category. A crash (`tab crashed`, `TimeoutException`, `ReadTimeoutError`) stores 0 rows; 46 runs did, wasting ~99.5 h (~19% of runtime). The run summary still prints `categories_succeeded=1 categories_failed=0`. Example: baby, 30 Sep, 1.6 h, nothing stored. Fix direction: write rows per page, mark partial/failed runs in the summary and in the data. The product-tile wait (`WebDriverWait(..., 15)` in `get_products`) still raises and discards the category, including after a pagination recovery.
2. **Partial categories stored as if complete.** ~25 runs hit the scraper's own "scrape gap" warning. Examples: pantry 1 Oct 2,569/8,268; drinks 572/2,435. Nothing marks the rows as partial.
3. **Unreliable expected total ("page data").** `get_category_total_items` often returns 10-20 or 0 when the page has not finished loading (almost every run on 29 Jun, still recurring: 22 Jul, 6 Aug, 19 Aug). Ignore values below ~50 and treat exactly 10,000 as a cap rather than a count.
4. **beer-wine-spirits repeats content.** It walks all ~51 pages but only ~630 of ~1,834 products are unique (71-79% duplicates versus ~50% elsewhere), so pages appear to repeat. Separate from the pagination bug. Only 2 complete runs exist.
5. **Badge text parsed as product name.** ~1,200 rows have names like `EST. RESTOCK dd/mm/yy` (796), `IN-STORE ONLY` (177), `[unknown]` (91), `Lowest price in N days` (77), `EVERYDAY LOW PRICE`, `SAVE $x`. The real name is lost. Early DEBUG output also showed names like `/ 100G`.
6. **Marketplace (third-party) items.** ~291k incomplete lines are missing only `unit_price`; nearly all are Marketplace sellers (Hoka, Birkenstock, treadmills...) which have no unit price. They make home-lifestyle 88% incomplete and also dominate pet, baby and cleaning. Consider tagging or excluding them.
7. **Per-page counts do not always reconcile.** 15 Jul dinner: pages summed to 158 scraped but the category reported 105. 19 pages where tiles != scraped.
8. **Runs that vanish.** Dairy 28 Jun, dairy 1 Jul and health-wellness 6 Aug have no summary or stored-rows line (process killed). The 12 Jun FULL run ended in read timeouts; 28 Jun FULL runs failed with `Category '' was not found`.
9. **No retry or resume at run level.** A failed 5-6 h category restarts from scratch.
10. **Chrome stability.** Frequent `tab crashed` in June/July (Chrome 147); mostly replaced by TimeoutExceptions since August.

## Fixed (uncommitted at time of writing)

- **Pagination ended on the first hiccup.** A hung browser mid-advance (120 s read timeout) or a next button not found within 2 s ended the category (`Pagination stop: ...`), causing the 1 Oct partials in beauty, health-wellness, pantry and personal-care. `web_driver.py` now retries on a fresh driver at `?pageNumber=N+1` (up to 3 attempts) and only accepts the end of pagination after a reload. Not yet validated against the live site; watch for `Pagination recovery` warnings in the next batch. Drinks (1 Oct) stopped without any pagination warning, so its cause is unconfirmed.

## Suggested order

1. Incremental saving plus honest run summary (issues 1, 2, 8).
2. Validate the pagination fix on a real batch; check drinks and beer-wine-spirits (4).
3. Total-count sanity checks (3).
4. Name-parsing fix (5), then Marketplace handling (6).
5. Optional: skip the duplicate tiles to halve per-page work.
