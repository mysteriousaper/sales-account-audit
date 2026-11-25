-- Rules for a public CRM export I did not create: Maven Analytics "CRM Sales Opportunities"
-- (8,800 opportunities, 35 agents). Written before looking at any results; there is no answer key.
-- Pipeline stages: Prospecting > Engaging > Won / Lost.

CREATE OR REPLACE TABLE m_flags AS
-- M1: closed deals (Won/Lost) need a close date; open deals must not have one
SELECT opportunity_id, sales_agent, 'M1_close_date_vs_stage' AS rule FROM sales_pipeline
WHERE (deal_stage IN ('Won','Lost') AND close_date IS NULL)
   OR (deal_stage IN ('Prospecting','Engaging') AND close_date IS NOT NULL)
UNION ALL
-- M2: every deal past Prospecting needs an engage date
SELECT opportunity_id, sales_agent, 'M2_missing_engage_date' FROM sales_pipeline
WHERE deal_stage IN ('Engaging','Won','Lost') AND engage_date IS NULL
UNION ALL
-- M3: a deal cannot close before it was engaged
SELECT opportunity_id, sales_agent, 'M3_closed_before_engaged' FROM sales_pipeline
WHERE close_date < engage_date
UNION ALL
-- M4: Won needs revenue, Lost should carry none
SELECT opportunity_id, sales_agent, 'M4_value_vs_stage' FROM sales_pipeline
WHERE (deal_stage = 'Won' AND coalesce(close_value, 0) <= 0)
   OR (deal_stage = 'Lost' AND coalesce(close_value, 0) <> 0)
UNION ALL
-- M5: product must exist in the product list
SELECT s.opportunity_id, s.sales_agent, 'M5_unknown_product' FROM sales_pipeline s
WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.product = s.product)
UNION ALL
-- M6: deals past Prospecting need an account that exists in the accounts table
SELECT s.opportunity_id, s.sales_agent, 'M6_missing_or_unknown_account' FROM sales_pipeline s
WHERE s.deal_stage <> 'Prospecting'
  AND (s.account IS NULL OR NOT EXISTS (SELECT 1 FROM accounts a WHERE a.account = s.account))
UNION ALL
-- M7: Won value far from list price (under 50% or over 150%) goes to review
SELECT s.opportunity_id, s.sales_agent, 'M7_price_outlier' FROM sales_pipeline s
JOIN products p ON p.product = s.product
WHERE s.deal_stage = 'Won' AND (s.close_value < 0.5 * p.sales_price OR s.close_value > 1.5 * p.sales_price)
UNION ALL
-- M8: deals sitting in Engaging for over 90 days before the last date in the export are stale
SELECT opportunity_id, sales_agent, 'M8_stale_engaging' FROM sales_pipeline
WHERE deal_stage = 'Engaging'
  AND engage_date < (SELECT max(close_date) FROM sales_pipeline) - INTERVAL 90 DAY
UNION ALL
-- M9: agent must be on the sales team list
SELECT s.opportunity_id, s.sales_agent, 'M9_unknown_agent' FROM sales_pipeline s
WHERE NOT EXISTS (SELECT 1 FROM sales_teams t WHERE t.sales_agent = s.sales_agent);
