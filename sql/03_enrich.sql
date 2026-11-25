-- Second data source: the public contractor-license registry.
-- Match on cleaned business name + city + state to fill missing phones and add license status.
CREATE OR REPLACE TABLE registry_clean AS
SELECT license_no, license_status, city, state,
       right(regexp_replace(CAST(phone AS VARCHAR), '[^0-9]', '', 'g'), 10) AS phone,
       trim(regexp_replace(regexp_replace(lower(business_name), '[^a-z0-9 ]', '', 'g'), '\s+', ' ', 'g')) AS name_key
FROM license_registry;

CREATE OR REPLACE TABLE enrichment AS
SELECT a.account_id, acc.status, r.license_no, r.license_status,
       (acc.phone IS NULL OR trim(acc.phone) = '') AS phone_was_missing,
       r.phone AS registry_phone
FROM accounts_clean a
JOIN accounts acc ON acc.account_id = a.account_id
JOIN registry_clean r
  ON r.name_key = a.name_key AND r.city = a.city AND r.state = a.state;
