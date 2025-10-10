# Data Product Costs Sync (Placeholder)

This workflow demonstrates how to attribute Databricks infrastructure costs to data products using system tables and upsert them into the app's `cost_items` table as monthly cost items with `cost_center=INFRASTRUCTURE`.

Reference: Monitor costs using system tables — https://docs.databricks.com/aws/en/admin/usage/system-tables

## Concept

- Use `system.billing.usage` joined with `system.billing.list_prices` to compute dollar cost
- Attribute usage to a data product via a tag (e.g., `data_product_id=<UUID>` on clusters/jobs)
- Aggregate by month and currency; upsert rows with:
  - title: "Databricks Infra Cost"
  - start_month = end_month = first day of month
  - amount_cents = round(total_dollars * 100)
  - currency from `list_prices`

## Sample SQL (adapt as needed)

```sql
-- Parameter: product_id UUID
-- Parameter: month_start DATE, month_end DATE (exclusive)
WITH usage_tagged AS (
  SELECT
    u.usage_date,
    u.usage_quantity,
    u.sku_name,
    u.custom_tags["data_product_id"] as product_id
  FROM system.billing.usage u
  WHERE u.custom_tags["data_product_id"] = :product_id
    AND u.usage_date >= :month_start
    AND u.usage_date < :month_end
), priced AS (
  SELECT
    SUM(u.usage_quantity * lp.pricing.effective_list.default) AS total_usd
  FROM usage_tagged u
  JOIN system.billing.list_prices lp
    ON lp.sku_name = u.sku_name
   AND u.usage_date >= lp.price_start_time
   AND (lp.price_end_time IS NULL OR u.usage_date < lp.price_end_time)
)
SELECT COALESCE(CAST(ROUND(total_usd * 100) AS BIGINT), 0) AS amount_cents
FROM priced;
```

## Upsert sketch (Python)

- Query the SQL above using your preferred client
- Insert or update into `cost_items` with
  - `entity_type='data_product'`, `entity_id=:product_id`
  - `cost_center='INFRASTRUCTURE'`, `currency='USD'` (or from pricing),
  - `title='Databricks Infra Cost'`, `start_month`, `end_month` set to the month

> This is a placeholder. Wire it to job runner infrastructure as needed.


