-- Same matching approach as the CRM contacts, run on FEBRL2: 5,000 person records from the
-- Febrl record-linkage benchmark (ANU), with typos, swapped fields and missing values added by
-- the benchmark authors, not by me. Compare only records sharing a postcode or a surname (blocking).
CREATE OR REPLACE TABLE febrl_clean AS
SELECT rec_id,
       lower(trim(coalesce(given_name, ''))) AS first_name,
       lower(trim(coalesce(surname, ''))) AS last_name,
       CAST(postcode AS VARCHAR) AS postcode,
       CAST(date_of_birth AS VARCHAR) AS dob,
       CAST(soc_sec_id AS VARCHAR) AS ssn,
       lower(trim(coalesce(address_1, ''))) AS address
FROM febrl_records;

CREATE OR REPLACE TABLE febrl_candidates AS
SELECT a.rec_id AS rec_a, b.rec_id AS rec_b,
       jaro_winkler_similarity(a.first_name, b.first_name) AS fn_sim,
       jaro_winkler_similarity(a.last_name, b.last_name) AS ln_sim,
       jaro_winkler_similarity(a.address, b.address) AS addr_sim,
       (a.dob = b.dob) AS same_dob, (a.ssn = b.ssn) AS same_ssn, (a.postcode = b.postcode) AS same_postcode
FROM febrl_clean a
JOIN febrl_clean b
  ON a.rec_id < b.rec_id
 AND (a.postcode = b.postcode OR a.last_name = b.last_name OR a.ssn = b.ssn);

-- Points system: each agreeing field adds evidence. High total = auto-merge, middle = review.
CREATE OR REPLACE TABLE febrl_matches AS
SELECT rec_a, rec_b,
       (CASE WHEN same_ssn THEN 3 ELSE 0 END) + (CASE WHEN same_dob THEN 2 ELSE 0 END)
     + (CASE WHEN fn_sim >= 0.85 THEN 1 ELSE 0 END) + (CASE WHEN ln_sim >= 0.85 THEN 1 ELSE 0 END)
     + (CASE WHEN addr_sim >= 0.85 THEN 1 ELSE 0 END) + (CASE WHEN same_postcode THEN 1 ELSE 0 END) AS points
FROM febrl_candidates;
