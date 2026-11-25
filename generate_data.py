"""
Generate a sample CRM export for an outbound sales team that sells software to trade
businesses (HVAC, plumbing, electrical, roofing, garage doors).

The data starts clean. Then known problems are injected on purpose and written to
truth_*.csv files, so the audit can be scored for accuracy afterwards.
All names, companies and numbers are made up.
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)
TODAY = date(2026, 11, 20)
OUT = "data/"

TRADES = ["HVAC", "Plumbing", "Electrical", "Roofing", "Garage Doors", "Pest Control"]
CITIES = [("Phoenix", "AZ"), ("Dallas", "TX"), ("Austin", "TX"), ("Atlanta", "GA"), ("Denver", "CO"),
          ("Tampa", "FL"), ("Charlotte", "NC"), ("Columbus", "OH"), ("Nashville", "TN"), ("Sacramento", "CA")]
WORDS = ["Apex", "Blue Sky", "Summit", "Precision", "Reliable", "Express", "Elite", "Pro", "Allied", "Liberty",
         "Patriot", "Comfort", "Rapid", "Premier", "Golden", "Northstar", "Ironclad", "Evergreen", "Cardinal", "Ace"]
FIRST = ["James", "Maria", "Robert", "Linda", "Michael", "Sarah", "David", "Karen", "Jose", "Emily", "Daniel",
         "Ashley", "Chris", "Jessica", "Kevin", "Laura", "Brian", "Megan", "Jason", "Nicole"]
LAST = ["Smith", "Johnson", "Garcia", "Brown", "Miller", "Davis", "Martinez", "Wilson", "Anderson", "Taylor",
        "Thomas", "Moore", "Jackson", "White", "Harris", "Clark", "Lewis", "Walker", "Young", "Hall"]
DM_TITLES = ["Owner", "President", "General Manager"]
OTHER_TITLES = ["Office Manager", "Dispatcher", "Service Manager", "Technician", "Bookkeeper"]
SUFFIXES = ["Services", "Co", "Pros", "Solutions", "Group"]
REPS = ["R%02d" % i for i in range(1, 13)]
# Some reps are sloppier than others, so the scorecard has something to find
REP_SLOPPINESS = {r: random.choice([0.05, 0.08, 0.12, 0.2, 0.3]) for r in REPS}
OPEN = ["Working", "Contacted", "Demo Scheduled"]


def phone():
    return "%03d%03d%04d" % (random.randint(200, 989), random.randint(200, 999), random.randint(0, 9999))


def fmt_phone(p, style):
    if style == 0:
        return "(%s) %s-%s" % (p[:3], p[3:6], p[6:])
    if style == 1:
        return "%s-%s-%s" % (p[:3], p[3:6], p[6:])
    return "+1 %s.%s.%s" % (p[:3], p[3:6], p[6:])


accounts, contacts, activities, truth_rules, truth_dup_contacts, truth_dup_accounts, registry = [], [], [], [], [], [], []
used_names = set()
cid = 0
aid_counter = 0

for i in range(5000):
    aid_counter += 1
    aid = "A%05d" % aid_counter
    while True:
        trade = random.choice(TRADES)
        name = "%s %s %s %s" % (random.choice(WORDS), random.choice(WORDS), trade, random.choice(SUFFIXES))
        if name not in used_names:
            used_names.add(name)
            break
    domain = name.lower().replace(" ", "") + ".com"
    city, state = random.choice(CITIES)
    owner = random.choice(REPS)
    status = random.choices(["New", "Working", "Contacted", "Demo Scheduled", "Disqualified"], [15, 35, 25, 10, 15])[0]
    acc_phone = phone()
    next_step = ""
    dq_reason = ""
    if status in OPEN:
        next_step = (TODAY + timedelta(days=random.randint(1, 21))).isoformat()
    if status == "Disqualified":
        dq_reason = random.choice(["Too small", "Using competitor", "Not a fit", "Out of business"])
    acc = {"account_id": aid, "account_name": name, "domain": domain, "phone": fmt_phone(acc_phone, random.randint(0, 2)),
           "city": city, "state": state, "trade": trade, "owner_rep": owner, "status": status,
           "next_step_date": next_step, "disqualify_reason": dq_reason}

    # Contacts: one decision maker for accounts past "New", plus 1-3 others
    acc_contacts = []
    n_other = random.randint(1, 3)
    titles = random.sample(OTHER_TITLES, n_other)
    if status != "New":
        titles = [random.choice(DM_TITLES)] + titles
    for t in titles:
        cid += 1
        fn, ln = random.choice(FIRST), random.choice(LAST)
        c = {"contact_id": "C%06d" % cid, "account_id": aid, "first_name": fn, "last_name": ln, "title": t,
             "email": "%s.%s@%s" % (fn.lower(), ln.lower(), domain), "phone": fmt_phone(phone(), random.randint(0, 2))}
        acc_contacts.append(c)

    # Activities: compliant baseline
    acts = []
    if status in ["Working", "Contacted"]:
        for k in range(random.randint(3, 6)):
            acts.append(("call" if random.random() < 0.6 else "email", owner, TODAY - timedelta(days=random.randint(0, 29))))
    if status == "Demo Scheduled":
        for k in range(random.randint(3, 5)):
            acts.append(("call", owner, TODAY - timedelta(days=random.randint(0, 29))))
        acts.append(("meeting", owner, TODAY - timedelta(days=random.randint(0, 10))))
    if status == "Disqualified":
        acts.append(("call", owner, TODAY - timedelta(days=random.randint(30, 120))))

    # Inject rule violations, more often for sloppy reps
    p = REP_SLOPPINESS[owner]
    if status in ["Working", "Contacted"] and random.random() < p:          # R1 too few touches
        acts = acts[:random.randint(0, 2)]
        truth_rules.append((aid, "R1_min_touches"))
    if status in ["Contacted", "Demo Scheduled"] and random.random() < p * 0.6:  # R2 no decision maker
        acc_contacts = [c for c in acc_contacts if c["title"] not in DM_TITLES]
        truth_rules.append((aid, "R2_decision_maker"))
    if status in OPEN and random.random() < p * 0.8:                       # R3 next step missing or overdue
        acc["next_step_date"] = random.choice(["", (TODAY - timedelta(days=random.randint(1, 40))).isoformat()])
        truth_rules.append((aid, "R3_next_step"))
    if status == "Demo Scheduled" and random.random() < p:                  # R4 demo stage without a meeting
        acts = [a for a in acts if a[0] != "meeting"]
        truth_rules.append((aid, "R4_demo_meeting"))
    if status == "Disqualified" and random.random() < p:                    # R5 no disqualify reason
        acc["disqualify_reason"] = ""
        truth_rules.append((aid, "R5_dq_reason"))
    if acts and random.random() < p * 0.4:                                  # R6 activity logged by a non-owner
        k = random.randrange(len(acts))
        other = random.choice([r for r in REPS if r != owner])
        acts[k] = (acts[k][0], other, acts[k][2])
        truth_rules.append((aid, "R6_owner_mismatch"))

    accounts.append(acc)
    contacts.extend(acc_contacts)
    for a in acts:
        activities.append({"account_id": aid, "rep": a[1], "type": a[0], "activity_date": a[2].isoformat()})

    # Inject duplicate contacts (same person entered again with messy formatting)
    if acc_contacts and random.random() < 0.06:
        src = random.choice(acc_contacts)
        cid += 1
        variant = random.randint(0, 2)
        dup = dict(src)
        dup["contact_id"] = "C%06d" % cid
        if variant == 0:
            # same email, different case and stray spaces
            dup["email"] = "  " + src["email"].upper()
        elif variant == 1:
            # no email, same phone written in another format
            digits = "".join(ch for ch in src["phone"] if ch.isdigit())[-10:]
            dup["email"] = ""
            dup["phone"] = fmt_phone(digits, random.randint(0, 2))
        else:
            # typo in the first name, no email or phone: only the name and company tell us
            fn = src["first_name"]
            dup["first_name"] = fn[:-1] if len(fn) > 4 else fn + "e"
            dup["email"] = ""
            dup["phone"] = ""
        contacts.append(dup)
        truth_dup_contacts.append((src["contact_id"], dup["contact_id"]))

    # Public contractor-license registry (a second data source). Covers most companies.
    if random.random() < 0.85:
        registry.append({"license_no": "LIC-%s-%06d" % (state, random.randint(0, 999999)), "business_name": name.upper(),
                         "city": city, "state": state, "phone": acc_phone, "license_status": random.choice(["Active"] * 9 + ["Expired"])})

# Inject duplicate accounts (same company created twice by different reps)
n_acc = len(accounts)
for src in random.sample(accounts[:n_acc], 110):
    aid_counter += 1
    dup = dict(src)
    dup["account_id"] = "A%05d" % aid_counter
    dup["owner_rep"] = random.choice([r for r in REPS if r != src["owner_rep"]])
    style = random.randint(0, 2)
    if style == 0:
        dup["account_name"] = src["account_name"] + " LLC"
    elif style == 1:
        dup["account_name"] = src["account_name"].upper()
        dup["domain"] = "www." + src["domain"]
    else:
        dup["account_name"] = src["account_name"].replace(" ", "  ", 1) + " Inc."
        dup["domain"] = "https://" + src["domain"] + "/"
    dup["status"] = "New"
    dup["next_step_date"] = ""
    dup["disqualify_reason"] = ""
    accounts.append(dup)
    truth_dup_accounts.append((src["account_id"], dup["account_id"]))

# Some accounts lost their phone number in the CRM (the registry can fill them)
for acc in random.sample(accounts, 400):
    acc["phone"] = ""


def write(name, rows, header=None):
    with open(OUT + name, "w", newline="") as f:
        if header:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        else:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)


write("accounts.csv", accounts)
write("contacts.csv", contacts)
write("activities.csv", activities)
write("license_registry.csv", registry)
write("truth_rule_violations.csv", truth_rules, ["account_id", "rule"])
write("truth_duplicate_contacts.csv", truth_dup_contacts, ["contact_id_a", "contact_id_b"])
write("truth_duplicate_accounts.csv", truth_dup_accounts, ["account_id_a", "account_id_b"])
print("accounts", len(accounts), "contacts", len(contacts), "activities", len(activities),
      "registry", len(registry), "seeded rule violations", len(truth_rules),
      "dup contacts", len(truth_dup_contacts), "dup accounts", len(truth_dup_accounts))
