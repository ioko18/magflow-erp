---
title: eMAG API Reference
last_reviewed: 2025-09-25
owner: integrations-team
---

# eMAG API Reference

This document condenses the operational details required to work with the eMAG Marketplace API v4.4.8 from inside MagFlow ERP. Use it as the single source of truth for protocol limits, authentication, and payload expectations.

## Authentication & Environment

- **Protocol**: HTTP(S) with JSON payloads encoded in UTF-8.
- **Auth**: Basic Auth (`username:password` → Base64) with IP whitelisting per account.
- **Base URLs**:
  - eMAG RO: `https://marketplace-api.emag.ro/api-3`
  - eMAG BG: `https://marketplace-api.emag.bg/api-3`
  - eMAG HU: `https://marketplace-api.emag.hu/api-3`
  - Fashion Days RO: `https://marketplace-ro-api.fashiondays.com/api-3`
  - Fashion Days BG: `https://marketplace-bg-api.fashiondays.com/api-3`
- **Environment variables** (prefix per account):
  - `EMAG_<ACCOUNT>_USERNAME`, `EMAG_<ACCOUNT>_PASSWORD`
  - `EMAG_<ACCOUNT>_ACCOUNT_TYPE` (`main` or `fbe`)
  - `EMAG_<ACCOUNT>_WAREHOUSE_ID`
  - `EMAG_<ACCOUNT>_IP_WHITELIST_NAME`
- **Timeouts**: Connect 10s, request 30s.
- **Secrets**: Never commit real passwords; rely on `.env` + deployment secret storage.

## Rate Limiting & Backoff

| Resource family | Limit | Notes |
| ---------------- | ----- | ----- |
| Orders endpoints | 12 req/s or 720 req/min | Apply jitter when scheduling jobs. |
| All other endpoints | 3 req/s or 180 req/min | Respect per-resource buckets. |

- Monitor headers: `X-RateLimit-Limit-3second`, `X-RateLimit-Remaining-3second`, `Retry-After`.
- Recommended retry: exponential backoff (2s, 4s, 8s) with a max of 3 attempts on 429/5xx.
- Keep burst usage under 80% of allowance; alert when sustained utilisation exceeds 0.8.

## Core Resources & Actions

| Resource | Actions | Highlights |
| -------- | ------- | ---------- |
| `product_offer` | `read`, `save`, `count` | Create & update products/offers. Enforce mutual exclusivity between `ean[]` and `part_number_key`. `sale_price` must be inside `min_sale_price`/`max_sale_price`. |
| `offer_stock` | `PATCH /offer_stock/{resourceId}` | Atomic stock updates. |
| `campaign_proposals` | `save` | Supports MultiDeals with `date_intervals`. |
| `order` | `read`, `save`, `count`, `acknowledge`, `unlock-courier` | Use incremental sync on `modified` timestamps. |
| `awb` | `save`, `read`, `read_pdf` | Include AWB type & locker flags where applicable. |
| `rma` | `read`, `save`, `count` | Supports `type` filters and status transitions. |
| `category`, `vat`, `handling_time`, `locality`, `courier_accounts` | `read`, `count` | Source-of-truth catalog metadata for validation. |

### Category Read — Categories, Characteristics & Family Types

#### General Behaviour

- Every product must belong to a category. Sellers cannot create or modify categories; they can publish only in allowed ones.
- `category/read` without parameters returns the first 100 active categories; use pagination to enumerate all categories.
- Reading a category by `id` returns the category details, available characteristics (with IDs), and available product `family_types` (with IDs).
- Fetching by `id` is the only reliable way to discover mandatory characteristics, restrictive rules, and the allowed values before sending product data.
- Additional pagination fields (API v4.4.8) for characteristics:
  - `valuesCurrentPage`
  - `valuesPerPage`
  Example payload:
  ```json
  {
    "id": 15,
    "valuesCurrentPage": 1,
    "valuesPerPage": 10
  }
  ```
- Resource/actions: `category` supports `read` and `count`.

#### Category (Level 1 Fields)

- `id` *(integer)*: eMAG category ID (e.g., `604`).
- `name` *(string)*: Category name (e.g., `"Music"`).
- `is_allowed` *(integer 0/1)*: Indicates whether the seller may post in this category (e.g., `0`).
- `parent_id` *(integer)*: Parent category ID (e.g., `12`).
- `is_ean_mandatory` *(integer 0/1)*: Whether EAN is mandatory when saving a product (e.g., `1`).
- `is_warranty_mandatory` *(integer 0/1)*: Whether warranty is mandatory on product save (e.g., `1`).

#### `characteristics` Array (returned fully when reading a single category)

For each characteristic:

- `id` *(integer)*: Characteristic ID (e.g., `38`).
- `name` *(string)*: Characteristic name (e.g., `"Audio"`).
- `type_id` *(integer)*: Accepted value type. Common examples:
  - Single-value types:
    - `1` = Numeric (e.g., `20`, `1`, `30`)
    - `60` = Size (e.g., `36 EU`, `XL INTL`)
    - `20` = Boolean (`Yes`/`No`/`N/A`)
  - Multi-value types:
    - `2` = Numeric + unit (e.g., `30 cm`, `20 GB`, `30 inch`)
    - `11` = Text Fixed (≤255 chars; e.g., `"Blue"`, `"Laptop"`, `"Woman"`)
    - `30` = Resolution (`Width x Height`, e.g., `"640 x 480"`)
    - `40` = Volume (`Width x Height x Depth - Depth2`, e.g., `"30 x 40 x 50 - 10"`)
- `display_order` *(integer)*: Display order (e.g., `6`).
- `is_mandatory` *(integer 0/1)*: Whether the characteristic is mandatory when sending the product (e.g., `0`).
- `is_filter` *(integer 0/1)*: Whether the characteristic is used as a site filter (e.g., `1`).
- `allow_new_value` *(integer 0/1)*: Whether new values can be auto-validated (e.g., `0`).
- `values` *(array)*: Up to the first 256 existing values for this characteristic (returned on single-category reads).
- `tags` *(array of strings)*: Required/optional tags for the characteristic. For size-related data, use characteristic `"Size"` (ID `6506`) with tags `"original"` and `"converted"`. Example payload:
  ```json
  {"id": 6506, "tag": "original", "value": "36 EU"},
  {"id": 6506, "tag": "converted", "value": "39 intl"}
  ```
  Example `tags` array: `["original", "converted"]`. Note: the legacy tag `"Converted Size"` (ID `10770`) is being removed.

#### `family_types` Array

Each family type entry includes:

- `id` *(integer)*: Family type ID (e.g., `95`).
- `name` *(string)*: Family name (e.g., `"Quantity"`).
- `characteristics` *(array)*: Defines how each characteristic is presented in this family type:
  - `characteristic_id` *(integer)* (e.g., `44`).
  - `characteristic_family_type_id` *(integer)*: Display method (1 = Thumbnails, 2 = Combobox, 3 = Graphic Selection).
  - `is_foldable` *(integer 0/1)*: When `1`, members with different values are grouped in listings.
  - `display_order` *(integer)*: Order within the family type.

#### Language Parameter

- By default, `category/read` returns names in the marketplace’s default language.
- Pass `language=<code>` to retrieve names in a specific language. Supported languages: `EN`, `RO`, `HU`, `BG`, `PL`, `GR`, `DE`.
- Example: `.../category/read?language=en`.

#### Example Request Combining `id` with Value Pagination

```json
{
  "id": 15,
  "valuesCurrentPage": 1,
  "valuesPerPage": 10
}
```

#### Notes

- Reading a category by `id` provides the full template (characteristics + family types). Use it to determine mandatory fields, filters, tagged values, and allowed values before publishing products.
- Code consuming this data (for example `app/integrations/emag/services/catalog_service.py` or `scripts/standalone_test_catalog.py`) must respect the mandatory flags, allowed-value lists, and tag semantics documented above.

### Product Offer Payload Essentials

```json
{
  "id": 123456,
  "category_id": 100,
  "name": "Product Name",
  "part_number": "PN-ABC-123",
  "ean": ["594***"],
  "description": "<p>Rich text</p>",
  "images": [{"url": "https://...", "display_type": 1}],
  "characteristics": [{"id": 6506, "value": "36 EU", "tag": "original"}],
  "sale_price": 199.99,
  "min_sale_price": 180.00,
  "max_sale_price": 220.00,
  "stock": [{"warehouse_id": 1, "value": 25}],
  "vat_id": 5,
  "handling_time": [{"warehouse_id": 1, "value": 1}],
  "status": 1,
  "start_date": "2025-01-15"
}
```

- Use `images_overwrite=1` to fully replace existing images.
- Provide `manufacturer[]` / `eu_representative[]` data for GPSR compliance when available.
- `green_tax` applies only on eMAG RO.

## Response Conventions & Error Handling

- Every response includes `isError`. Treat missing or `true` values as failure.
- Validation errors surface through `messages[]` with `code`/`message` pairs.
- Common error codes:
  - `AUTH_INVALID_CREDENTIALS`
  - `AUTH_IP_NOT_WHITELISTED`
  - `RATE_LIMIT_EXCEEDED`
  - `VALIDATION_MISSING_FIELD`
  - `BUSINESS_DUPLICATE_SKU`
- Log the full request/response body with correlation IDs for 30 days.

### Retry & Circuit Breaker Guidelines

- Trigger circuit breaker after 5 consecutive non-retryable failures. Provide `retry_after` where possible.
- Handle 401/403 by refreshing credentials or updating the IP whitelist.
- Implement batch processing for large datasets (≤50 entities per bulk call, ≤4000 input vars).

## Testing & Tooling

- Integration pytest entry point: `pytest tests/integration/emag -vv --no-cov`.
- Smoke tests:
  - `tests/integration/emag/test_client.py::test_make_request_rate_limit`
  - `tests/integration/emag/test_client.py::test_circuit_breaker`
- Use the `test_emag_credentials.sh` helper for manual credential checks.

## Operational Checklists

- **Before sync**: confirm rate-limit configuration, credentials, and whitelisted IPs.
- **During sync**: monitor response times, error rate, and rate-limit headroom.
- **After sync**: export and archive sync results using `EmagIntegrationService.export_sync_data()`.

## Related Documents

- `docs/integrations/emag/integration_overview.md`
- `docs/EMAG_FULL_SYNC_GUIDE.md`
- `docs/EMAG_CREDENTIALS_TESTING_GUIDE.md`
- `docs/integrations/emag/catalog.md`
