# Account audit: findings for the outbound sales manager

**Data:** synthetic CRM export, 12 reps, 4,308 worked accounts, audit date 20 Nov 2026. The numbers show what the audit produces. They are not a statement about any real team.

## What I found

1. **A quarter of worked accounts break at least one rule (1,015 of 4,308).** The two most common problems are thin follow-up and lapsed next steps. Fewer than 3 touches in 30 days affects 349 accounts. A missing or overdue next step affects 333.
2. **The problem is concentrated.** Three reps (R08, R10, R11) fail on 42–57% of their accounts. The other nine sit between 9% and 24%. R08's main issue is touch cadence. R10 and R11 mostly let next steps go overdue.
3. **208 accounts have activity logged by a rep who doesn't own them,** and 110 accounts exist twice under two different reps. Both blur who is accountable for an account.
4. **Some data can't be trusted as it stands.** 44 contact pairs share an email but have different titles and phones. They were sent to review rather than merged. 285 open accounts belong to companies whose contractor license has expired.

## What I'd recommend

- Review R08, R10 and R11's books with them this week, starting with accounts that have an overdue next step. This is the quickest fix to verify.
- Merge the 110 duplicate accounts. Agree ownership first, using the rep with the most recent activity.
- Ask reps to confirm the 285 expired-license accounts before the next call, and drop the ones that have closed.
- Run the audit weekly and track each rep's failure rate over time, rather than as a one-off score.

## How much to trust this

The six rules caught every problem seeded in the test data, with no false flags. The duplicate matching was also tested on public benchmark data I did not create (FEBRL3): it gave 100% precision and 97.1% recall. The same SQL ran on 1 million accounts in under a second.

## Addendum: the same approach on a public CRM export

On Maven Analytics' public CRM export (8,800 opportunities), the rules found three things a manager would act on:

1. 729 won deals ($3.51M, 35% of won revenue) are logged under a product name, "GTXPro", that is not in the product list, so they vanish from price-list reports. **Fix:** map the name and lock the product field to a picklist.
2. 93% of Engaging deals (1,479 of 1,589) have not moved in over 90 days. **Fix:** a pipeline review with each agent, starting with the five who hold the most stale deals.
3. 68% of Engaging deals have no account attached. **Fix:** make Account required before a deal can move to Engaging.
