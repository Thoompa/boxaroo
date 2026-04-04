# Boxaroo Test Suite - BDD Scenarios

## Legend
- ✅ **Existing** - Test already implemented
- 🔨 **Priority** - High priority gaps to implement
- 📋 **Nice-to-have** - Additional coverage
- ❌ **Critical** - Must have before production

---

## 1. CLI & Parameter Handling

### 1.1 List Size Parameter ❌ CRITICAL
**Given** the application is launched with `--list_size TESTING` ✅
**When** the application initializes
**Then** only the TESTING dataset is processed

**Given** the application is launched with `--list_size FULL` ✅
**When** the application initializes
**Then** all categories are processed

**Given** the application is launched with `--list_size SHORT` ✅
**When** the application initializes
**Then** a limited subset of categories is processed

**Given** the application is launched with an invalid `--list_size INVALID` 📋 NICE-TO-HAVE
**When** the application initializes
**Then** an error message is displayed and app exits gracefully

### 1.2 Logging Level Parameter ❌ CRITICAL
**Given** the application is launched with `--logging_level DEBUG` ✅
**When** the application runs
**Then** DEBUG level messages are logged (verbose output)

**Given** the application is launched with `--logging_level INFO` ✅
**When** the application runs
**Then** only INFO and above messages are logged

**Given** the application is launched with `--logging_level ERROR` ✅
**When** the application runs
**Then** only ERROR messages are logged

**Given** the application is launched with an invalid `--logging_level INVALID` 📋 NICE-TO-HAVE
**When** the application initializes
**Then** an error message is displayed or default level is used

---

## 2. Web Driver & Page Loading

### 2.1 Base URL Loading ❌ CRITICAL
**Given** the Woolworths base URL
**When** WebDriver.get_page() is called
**Then** the page loads without errors
**Then** the DOM is accessible

**Given** the Woolworths base URL
**When** the page loads
**Then** the page contains expected elements (product tiles, category list)

### 2.2 Page Reload ❌ CRITICAL
**Given** a page is already loaded
**When** WebDriver.reload_page() is called
**Then** the page is reloaded
**Then** the DOM state is reset

**Given** a page reload is attempted
**When** a network error occurs
**Then** the error is caught and logged
**Then** a retry loop is executed (max retries 5 in prod; overridden to 1 in test)
**Then** after retries are exhausted the failure is surfaced gracefully

### 2.3 WebDriver Initialization & Cleanup ❌ CRITICAL
**Given** WebDriver is initialized
**When** the driver is configured
**Then** Selenium options are applied correctly (user agent, anti-detection)

**Given** the application completes
**When** WebDriver.quit() is called
**Then** the browser process is terminated
**Then** all resources are released

### 2.4 Category Total Items Extraction ✅ EXISTING
**Given** a category page is loaded
**When** get_category_total_items() is called with selector match
**Then** the item count is extracted from "Showing X products" text → `test_get_category_total_items_from_selector`

**Given** a category page is loaded
**When** get_category_total_items() is called with no selector match
**Then** fallback to wc-product-tile count is used → `test_get_category_total_items_fallback_to_tile_count`

**Given** a category page with no product count info
**When** get_category_total_items() is called
**Then** a default value (0) is returned

### 2.5 Category List Retrieval 🔨 PRIORITY
**Given** home page is loaded
**When** get_category_list() is called
**Then** returns list of categories with names and URLs

**Given** HTML has both primary and secondary selectors variant
**When** get_category_list() is called
**Then** returns categories from either selector pattern

**Given** page has no categories
**When** get_category_list() is called
**Then** warning is logged and empty list is returned

**Given** some categories are known to be broken  🔨 PRIORITY
**When** get_category_list() is called
**Then** broken ones are skipped and logged (with details)

**Given** category list is expected to be used for TESTING selection
**When** smallest stable category is selected
**Then** category with least pages/items is chosen (TODO: selection behavior)

---

## 3. Product Parsing & Extraction

### 3.1 Product Data Parsing ✅ EXISTING (3/4 tests)
**Given** complete product text with price, unit price, promotion, and name
**When** _parse_product_data() is called
**Then** returns `[name, price, unit_price, promotion]` → `test_parse_product_data_full`

**Given** product text with missing price/unit info
**When** _parse_product_data() is called
**Then** missing fields are empty strings → `test_parse_product_data_missing_price_unit`

**Given** null/invalid input to _parse_product_data()
**When** _parse_product_data(None) is called
**Then** returns `["", "", "", ""]` → `test_parse_product_data_non_string`

**Given** product text with only name
**When** _parse_product_data() is called
**Then** name is captured, prices are empty strings

**Given** malformed product text with unexpected format
**When** _parse_product_data() is called
**Then** no exception is raised
**Then** partial data is returned where possible

### 3.2 DOM Element Extraction 🔨 PRIORITY
**Given** an HTML element with visible text
**When** _get_product_string_from_element() is called
**Then** element.text content is returned

**Given** an HTML element with shadow DOM content
**When** _get_product_string_from_element() is called
**Then** JavaScript is executed to extract shadow root content → `test_get_product_string_from_element_with_shadow_root`

**Given** an HTML element with empty text and no shadow root
**When** _get_product_string_from_element() is called
**Then** an empty string is returned

**Given** an invalid/null element reference
**When** _get_product_string_from_element() is called
**Then** an exception is caught and handled
**Then** an error is logged

### 3.3 Product Batch Processing ✅ EXISTING
**Given** a list of product elements
**When** _get_products_data() processes them
**Then** complete products are added to results["products"]
**Then** incomplete products are tracked in results["incomplete_items"] → `test_get_products_data_incomplete_tracking`

**Given** an empty product list
**When** _get_products_data() is called
**Then** returns empty products and incomplete_items lists

**Given** a product that fails to parse
**When** _get_products_data() processes it
**Then** it's marked as incomplete
**Then** error details are captured

---

## 4. Page Pagination & Statistics

### 4.1 Page Loading & Pagination 🔨 PRIORITY
**Given** a category has multiple pages
**When** get_products() processes page 1
**Then** all products from page 1 are scraped

**Given** a category with multiple pages
**When** pagination to next page occurs
**Then** new products are loaded
**Then** page counter increments

**Given** the last page of results
**When** attempting to paginate further
**Then** pagination stops
**Then** no duplicate products are added

### 4.2 Page Statistics Aggregation ✅ EXISTING
**Given** products scraped from one page
**When** get_products() completes
**Then** page_stats contains: page number, tile count, scraped count, incomplete count → `test_get_products_page_stats_aggregation`

**Given** multiple pages are scraped
**When** final statistics are compiled
**Then** aggregated stats show total across all pages
**Then** per-page breakdown is available

---

## 5. File I/O & Data Persistence

### 5.1 CSV File Creation ❌ CRITICAL
**Given** scraped product data
**When** store_data() is called
**Then** a CSV file is created
**Then** file is saved to `Data/<YYYY-MM-DD>/woolworths-<YYYY-MM-DD>-<size>.csv`

**Given** CSV file data
**When** the file is opened
**Then** header row contains: name, price, unit_price, promotion

**Given** multiple product rows
**When** saved to CSV
**Then** each product is a separate row
**Then** data integrity is maintained (no data loss/corruption)

### 5.2 Directory Management 🔨 PRIORITY
**Given** the Data directory doesn't exist
**When** store_data() is called
**Then** the directory structure is created automatically

**Given** a date directory already exists and CSV file exists
**When** new data is saved
**Then** data is appended to the existing file
**Then** log indicates data already existed and line number where new data starts
**Then** duplicates are handled appropriately (future feature: read existing data to detect duplicates)

---

## 6. Logging & Observability

### 6.1 Application Header Log ❌ CRITICAL
**Given** the application starts
**When** logger.log() is called with application info
**Then** startup message is logged with timestamp and version

### 6.2 Per-Category Log ❌ CRITICAL
**Given** a category is being processed
**When** category processing begins
**Then** "Processing <category_name>" is logged
**Then** log includes category URL

**Given** category processing completes
**When** logger.log() is called
**Then** log includes: category name, items expected, items scraped, incomplete count

### 6.3 Per-Page Log ❌ CRITICAL
**Given** a page is being processed within a category
**When** page processing begins
**Then** "Page <N>" is logged
**Then** log includes tile count on page

**Given** page processing completes
**When** logger.log() is called
**Then** log includes: page number, scraped count, incomplete count

### 6.4 Per-Item Debug Log 📋 NICE-TO-HAVE
**Given** DEBUG logging is enabled
**When** each product is parsed
**Then** "Parsed product: <name>" is logged

**Given** DEBUG logging is enabled
**When** incomplete item occurs
**Then** "Incomplete item: <name>, missing: [fields]" is logged

### 6.5 Summary Log ❌ CRITICAL
**Given** scraping completes
**When** logger.log() called for summary
**Then** log includes:
  - Total categories attempted
  - Total categories succeeded
  - Total categories failed
  - Total items expected
  - Total items scraped
  - Total incomplete items
  - Duplicate list (if duplicates were detected)
  - Data file saved location
  - Runtime duration (whole run + each category)

**Then** log writes a "Manual Review" section immediately before the summary, including:
  - incomplete items + reason
  - duplicate candidate items with difference flags
  - errored items (failed parse, network etc.)
  - mis-parsed item details (with item name and page link)

**Given** scraping completes with incomplete items
**When** manual review section is written
**Then** each incomplete item includes name, missing fields, and page link

**Given** scraping completes with duplicate candidates
**When** manual review section is written
**Then** duplicate groups are listed with field differences flagged

**Given** scraping completes with parse errors
**When** manual review section is written
**Then** errored items are listed with error type and page link

### 6.6 Error Logging ❌ CRITICAL
**Given** an error occurs during scraping
**When** logger.error() is called
**Then** error message is logged
**Then** stack trace or context is included

---

## 7. Integration & End-to-End

### 7.1 Full Scrape Workflow ❌ CRITICAL (New)
**Given** `python __main__.py --list_size TESTING --logging_level INFO`
**When** the entire application runs
**Then** all test categories are processed
**Then** CSV file is created in Data/
**Then** Log file is created in Logs/
**Then** app exits with code 0

### 7.2 Category Workflow ❌ CRITICAL (New)
**Given** a specific category is selected
**When** scraping that category
**Then** page 1 is loaded
**Then** all pages are iterated
**Then** category finally data is saved

### 7.3 Data Output Validation ❌ CRITICAL (New)
**Given** scraping completes
**When** the output CSV file is read
**Then** every row has required fields (name at minimum)
**Then** no duplicate products exist
**Then** all data is properly formatted

---

## 8. Error Handling & Edge Cases

### 8.1 Network Errors 🔨 PRIORITY
**Given** a network timeout occurs
**When** get_page() is called
**Then** error is caught
**Then** error is logged
**Then** app retries or gracefully degrades

**Given** a 404 or invalid URL
**When** get_page() is called
**Then** error is logged
**Then** app continues or stops based on criticality

### 8.2 Parsing Errors 🔨 PRIORITY
**Given** malformed HTML structure
**When** product parsing occurs
**Then** no exception is raised
**Then** partial data is recovered where possible

**Given** unexpected element selectors
**When** elements are queried
**Then** empty results are handled gracefully

### 8.3 File System Errors
**Given** insufficient disk space
**When** store_data() is called
**Then** error is caught and logged
**Then** user is notified

**Given** file permissions issue
**When** store_data() attempts to write
**Then** error is logged
**Then** app continues without crash

### 8.4 Empty Results 📋 NICE-TO-HAVE
**Given** a category has no products
**When** the category is processed
**Then** log shows 0 items
**Then** empty CSV is created

**Given** all products on a page are incomplete
**When** page is processed
**Then** page_stats shows scraped=0, incomplete=N
**Then** data is still recorded

---

## 9. Data Quality & Validation

### 9.1 Incomplete Item Tracking 📋 NICE-TO-HAVE
**Given** a product missing unit_price
**When** tracked in incomplete_items
**Then** exception details show missing fields

**Given** multiple products with different missing fields
**When** aggregated
**Then** summary shows most common missing fields

### 9.2 Duplicate Detection 📋 NICE-TO-HAVE
**Given** the same product appears on multiple pages
**When** deduplication logic applies
**Then** product is recorded only once

---

## Test Implementation Priority

### Phase 1: CRITICAL ❌ (Must have for MVP)
- 1.1, 1.2 (CLI parameters) ✅
- 2.1, 2.2, 2.3 (WebDriver lifecycle)
- 6.1, 6.2, 6.3, 6.5, 6.6 (Logging)
- 7.1, 7.2, 7.3 (Integration)

### Phase 2: PRIORITY 🔨 (Important gaps)
- 2.5.4 (Broken categories)
- 3.2 (DOM extraction edge cases)
- 4.1 (Pagination)
- 5.2 (Directory management)
- 8.1, 8.2, 8.3 (Error handling)

### Phase 3: NICE-TO-HAVE 📋 (Polish)
- 1.1.4, 1.2.4 (CLI parameters edge cases)
- 3.1.4, 3.1.5 (Parsing edge cases)
- 6.4 (Debug logging)
- 8.4 (Empty results)
- 9.1, 9.2 (Data quality)

---

## Test Count Summary


| Category         | Total | Existing | Gap |
|------------------|-------|----------|-----|
| CLI Parameters   | 8     | 6        | 2   |
| Web Driver       | 13    | 2        | 11  |
| Product Parsing  | 9     | 3        | 6   |
| Pagination       | 5     | 1        | 4   |
| File I/O         | 5     | 0        | 5   |
| Logging          | 15    | 0        | 15  |
| Integration      | 3     | 0        | 3   |
| Error Handling   | 8     | 0        | 8   |
| Data Quality     | 4     | 0        | 4   |
| **TOTAL**        | **70**| **12**   | **58** |

**Current coverage: 17% → Target with implementation: 100%**
