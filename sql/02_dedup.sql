-- Clean versions of the fields we match on
CREATE OR REPLACE TABLE contacts_clean AS
SELECT contact_id, account_id, title,
       lower(trim(first_name)) AS first_name,
       lower(trim(last_name))  AS last_name,
       NULLIF(lower(trim(email)), '') AS email,
       NULLIF(right(regexp_replace(CAST(phone AS VARCHAR), '[^0-9]', '', 'g'), 10), '') AS phone
FROM contacts;

-- Duplicate contacts inside the same account, with the reason for each match
CREATE OR REPLACE TABLE dup_contacts AS
SELECT a.contact_id AS contact_id_a, b.contact_id AS contact_id_b, a.account_id,
       CASE WHEN a.email = b.email THEN 'same email'
            WHEN a.phone = b.phone THEN 'same phone and last name'
            ELSE 'similar first name, same last name and title' END AS match_reason,
       -- Same email but a different title AND a different phone is often two people
       -- (or a shared inbox). Those go to a person for review instead of an automatic merge.
       CASE WHEN a.email = b.email AND a.title <> b.title
                 AND a.phone IS NOT NULL AND b.phone IS NOT NULL AND a.phone <> b.phone
            THEN 'review' ELSE 'auto-merge' END AS decision
FROM contacts_clean a
JOIN contacts_clean b
  ON a.account_id = b.account_id
 AND a.contact_id < b.contact_id
WHERE a.email = b.email
   OR (a.phone = b.phone AND a.last_name = b.last_name)
   OR (a.last_name = b.last_name AND a.title = b.title
       AND jaro_winkler_similarity(a.first_name, b.first_name) >= 0.85);

-- Accounts: normalize the website and the company name
CREATE OR REPLACE TABLE accounts_clean AS
SELECT account_id, owner_rep, city, state,
       regexp_replace(regexp_replace(lower(trim(domain)), '^(https?://)?(www\.)?', ''), '/+$', '') AS domain,
       trim(regexp_replace(regexp_replace(lower(account_name), '[^a-z0-9 ]', '', 'g'),
                           '\s+(llc|inc)$|\s+', ' ', 'g')) AS name_key
FROM accounts;

-- Duplicate accounts: same website, or same normalized name in the same city
CREATE OR REPLACE TABLE dup_accounts AS
SELECT a.account_id AS account_id_a, b.account_id AS account_id_b,
       a.owner_rep AS owner_a, b.owner_rep AS owner_b,
       CASE WHEN a.domain = b.domain THEN 'same website' ELSE 'same name and city' END AS match_reason
FROM accounts_clean a
JOIN accounts_clean b
  ON a.account_id < b.account_id
 AND (a.domain = b.domain OR (a.name_key = b.name_key AND a.city = b.city));
