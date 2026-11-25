-- Account-work rules: one row per account that breaks a rule.
-- "Today" for the audit is 2026-11-20.

CREATE OR REPLACE TABLE rule_flags AS

-- R1: accounts in Working or Contacted need at least 3 touches (calls or emails) in the last 30 days
SELECT a.account_id, a.owner_rep, 'R1_min_touches' AS rule
FROM accounts a
LEFT JOIN activities t
       ON t.account_id = a.account_id
      AND t.type IN ('call', 'email')
      AND t.activity_date >= DATE '2026-11-20' - INTERVAL 30 DAY
WHERE a.status IN ('Working', 'Contacted')
GROUP BY a.account_id, a.owner_rep
HAVING COUNT(t.account_id) < 3

UNION ALL
-- R2: accounts in Contacted or Demo Scheduled need a decision maker on file
SELECT a.account_id, a.owner_rep, 'R2_decision_maker'
FROM accounts a
WHERE a.status IN ('Contacted', 'Demo Scheduled')
  AND NOT EXISTS (SELECT 1 FROM contacts c
                  WHERE c.account_id = a.account_id
                    AND c.title IN ('Owner', 'President', 'General Manager'))

UNION ALL
-- R3: open accounts need a next step dated today or later
SELECT a.account_id, a.owner_rep, 'R3_next_step'
FROM accounts a
WHERE a.status IN ('Working', 'Contacted', 'Demo Scheduled')
  AND (a.next_step_date IS NULL OR a.next_step_date < DATE '2026-11-20')

UNION ALL
-- R4: Demo Scheduled must have a logged meeting
SELECT a.account_id, a.owner_rep, 'R4_demo_meeting'
FROM accounts a
WHERE a.status = 'Demo Scheduled'
  AND NOT EXISTS (SELECT 1 FROM activities t
                  WHERE t.account_id = a.account_id AND t.type = 'meeting')

UNION ALL
-- R5: disqualified accounts need a reason
SELECT a.account_id, a.owner_rep, 'R5_dq_reason'
FROM accounts a
WHERE a.status = 'Disqualified'
  AND (a.disqualify_reason IS NULL OR trim(a.disqualify_reason) = '')

UNION ALL
-- R6: activity on an account logged by a rep who does not own it
SELECT DISTINCT a.account_id, a.owner_rep, 'R6_owner_mismatch'
FROM accounts a
JOIN activities t ON t.account_id = a.account_id
WHERE t.rep <> a.owner_rep;
