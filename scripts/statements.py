#!/usr/bin/env python3
"""Statement analyser for Wealth Guide Germany. Standard library only.

Turns account statements into the figures the specialists work from.

    python3 statements.py spending giro.csv [more.csv ...] [--json]
    python3 statements.py portfolio holdings.csv [--allowance 2000] [--church 0.09] [--marginal 0.42] [--json]
    python3 statements.py --selftest

spending   reads bank exports (CSV from German online banking, or a normalised
           file with the columns date,amount,counterparty,description) and
           reports income, spending by category, recurring payments, fees and
           money already going into savings.
portfolio  reads a holdings file with the columns
           name,isin,type,quantity,cost_basis,value,ter,monthly_plan,bought
           (type: etf_equity, etf_bond, etf_mixed, fund_active, stock, crypto,
           gold, cash, other; ter in percent; bought as YYYY-MM-DD, optional)
           and reports weights, concentration, cost, unrealised gains, the tax
           that selling would trigger and a rule-based note per position.

The notes are about structure, cost, tax and concentration. They are never a
view on whether a company or a market will do well.
"""
import csv
import io
import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime
# ---------------------------------------------------------------- parsing
DATE_COLS = ("buchungstag", "buchungsdatum", "buchung", "datum", "date", "valuta", "wertstellung")
AMOUNT_COLS = ("betrag", "umsatz", "amount", "betrag (eur)", "betrag (€)", "umsatz in eur")
DEBIT_COLS = ("soll", "ausgang", "belastung")
CREDIT_COLS = ("haben", "eingang", "gutschrift")
PARTY_COLS = ("counterparty", "name zahlungsbeteiligter", "beguenstigter/zahlungspflichtiger",
              "begünstigter/zahlungspflichtiger", "auftraggeber/empfänger", "auftraggeber / begünstigter",
              "zahlungsempfänger", "zahlungsempfänger*in", "empfänger", "empfaenger", "auftraggeber",
              "name", "partner", "gegenkonto name")
TEXT_COLS = ("description", "verwendungszweck", "buchungstext", "beschreibung", "text", "vorgang", "umsatzart")


def parse_amount(s):
    """'1.234,56' / '-1.234,56 €' / '1,234.56' / '12,50-' / '12,50 S' -> float."""
    if s is None:
        return None
    t = str(s).strip().replace("€", "").replace("EUR", "").replace(" ", "").replace(" ", "")
    if not t:
        return None
    neg = False
    if t.endswith("-") or t.upper().endswith("S"):
        neg, t = True, t[:-1]
    elif t.upper().endswith("H") or t.endswith("+"):
        t = t[:-1]
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1]
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    elif t.count(".") == 1 and len(t.split(".")[1]) == 3 and t.replace("-", "").split(".")[0] != "0":
        t = t.replace(".", "")          # 1.234 with German thousands separator
    try:
        v = float(t)
    except ValueError:
        return None
    return -abs(v) if neg else v


def parse_date(s):
    s = (s or "").strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10] if fmt != "%d.%m.%y" else s[:8], fmt).date()
        except ValueError:
            continue
    return None


def _read_text(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", "replace")


def _find(header, names):
    low = [h.strip().strip('"').lower() for h in header]
    for n in names:                       # exact match first, then prefix
        if n in low:
            return low.index(n)
    for n in names:
        for i, h in enumerate(low):
            if h.startswith(n):
                return i
    return None


def read_transactions(path):
    """Return a list of dicts: date, amount, party, text. Skips preamble lines."""
    lines = _read_text(path).splitlines()
    start, delim = None, ";"
    for i, line in enumerate(lines[:60]):
        d = max(";,\t", key=line.count)
        cells = next(csv.reader([line], delimiter=d), [])
        if len(cells) >= 3 and _find(cells, DATE_COLS) is not None \
                and _find(cells, AMOUNT_COLS + DEBIT_COLS) is not None:
            start, delim = i, d
            break
    if start is None:
        raise ValueError(f"{path}: no header row with a date and an amount column found")
    rows = list(csv.reader(io.StringIO("\n".join(lines[start:])), delimiter=delim))
    head = rows[0]
    ci = dict(date=_find(head, DATE_COLS), amount=_find(head, AMOUNT_COLS), debit=_find(head, DEBIT_COLS),
              credit=_find(head, CREDIT_COLS), party=_find(head, PARTY_COLS), text=_find(head, TEXT_COLS))
    out = []
    for r in rows[1:]:
        def cell(k):
            i = ci[k]
            return r[i].strip() if i is not None and i < len(r) else ""
        d = parse_date(cell("date"))
        if d is None:
            continue
        amt = parse_amount(cell("amount")) if ci["amount"] is not None else None
        if amt is None:
            deb, cred = parse_amount(cell("debit")), parse_amount(cell("credit"))
            if deb is None and cred is None:
                continue
            amt = (cred or 0.0) - abs(deb or 0.0)
        out.append({"date": d, "amount": amt, "party": cell("party"), "text": cell("text")})
    return out


# ---------------------------------------------------------- categorising
# Order matters: first match wins. Keywords are matched on lower-case text.
RULES = [
    ("income_salary", ("gehalt", "lohn", "bezüge", "bezuege", "entgelt", "vergütung", "verguetung", "salary", "payroll")),
    ("income_benefits", ("familienkasse", "kindergeld", "elterngeld", "bundesagentur", "rentenversicherung", "wohngeld")),
    ("investing", ("trade republic", "scalable", "sparplan", "wertpapier", "depot", "flatex", "smartbroker", "etf",
                   "comdirect wp", "consorsbank wp", "justtrade", "finanzen.net zero", "bitpanda", "coinbase", "kraken",
                   "bison", "union investment", "deka", "dws", "bauspar", "altersvorsorge", "riester", "rürup")),
    ("transfer_own", ("umbuchung", "übertrag", "uebertrag", "eigene konten", "tagesgeld", "festgeld", "own transfer")),
    ("tax", ("finanzamt", "steuerkasse", "bundeskasse", "kfz-steuer", "kfz steuer")),
    ("fees_interest", ("kontoführung", "kontofuehrung", "entgeltabschluss", "sollzins", "überziehung", "dispo",
                       "kartenpreis", "jahresgebühr", "kontogebühr", "abschluss", "zinsen kredit")),
    ("loan", ("darlehen", "kreditrate", "ratenkredit", "kreditvertrag", "tilgung", "rate", "leasing", "klarna", "paypal ratenzahlung", "santander consumer",
              "targobank", "auxmoney", "kfw studien", "bafög", "bafoeg")),
    ("housing", ("miete", "kaltmiete", "warmmiete", "mietzahlung", "hausverwaltung", "wohnungs", "vonovia", "deutsche wohnen",
                 "degewo", "gewobag", "howoge", "nebenkosten", "hausgeld", "grundsteuer")),
    ("utilities", ("strom", "ökostrom", "gas", "stadtwerke", "vattenfall", "eon", "e.on", "enbw", "rwe", "gasag", "wasserbetriebe",
                   "fernwärme", "heizung", "rundfunk", "beitragsservice", "abfall", "bsr ")),
    ("telecom", ("telekom", "vodafone", "o2", "telefonica", "1&1", "congstar", "aldi talk", "freenet", "pyur", "internet")),
    ("insurance", ("versicherung", "allianz", "huk", "ergo", "axa", "debeka", "signal iduna", "generali", "r+v",
                   "hannoversche", "cosmos", "getsafe", "wgv", "barmer", "techniker", "aok", "dak", "krankenkasse")),
    ("subscriptions", ("netflix", "spotify", "disney", "prime video", "amazon prime", "apple.com/bill", "icloud",
                       "youtube", "dazn", "sky ", "wow ", "audible", "adobe", "microsoft", "google one", "openai",
                       "claude", "anthropic", "dropbox", "zeit ", "spiegel", "faz", "sz ", "abo", "mitgliedschaft",
                       "fitness", "mcfit", "urban sports", "clever fit", "john reed", "verein")),
    ("children", ("kita", "kindergarten", "hort", "schule", "nachhilfe", "babysitter", "tagesmutter", "musikschule",
                  "spielwaren", "smyths")),
    ("groceries", ("rewe", "edeka", "aldi", "lidl", "penny", "netto", "kaufland", "denns", "bio company", "alnatura",
                   "dm", "rossmann", "budni", "müller drog", "flink", "gorillas", "picnic", "hit markt", "globus",
                   "tegut", "supermarkt", "biomarkt", "getränke", "bäckerei", "baeckerei", "metzger")),
    ("eating_out", ("restaurant", "lieferando", "wolt", "uber eats", "mcdonald", "burger king", "starbucks", "cafe",
                    "café", "pizza", "imbiss", "bistro", "kantine", "bar ", "gastro", "sushi", "döner", "doener")),
    ("transport", ("bvg", "deutsche bahn", "db vertrieb", "db fernverkehr", "deutschlandticket", "s-bahn", "mvg", "hvv",
                   "vbb", "tankstelle", "aral", "shell", "esso", "total", "jet ", "tanken", "adac", "tüv", "tuev",
                   "werkstatt", "share now", "miles", "sixt", "bolt", "uber", "freenow", "tier ", "lime", "parken",
                   "flixbus", "nextbike")),
    ("health", ("apotheke", "arzt", "praxis", "zahnarzt", "optiker", "fielmann", "physio", "klinik", "sanitätshaus")),
    ("travel", ("booking", "airbnb", "lufthansa", "ryanair", "easyjet", "eurowings", "hotel", "expedia", "tui",
                "check24 reise", "hostel", "condor")),
    ("shopping", ("amazon", "zalando", "h&m", "zara", "ikea", "mediamarkt", "media markt", "saturn", "otto", "ebay",
                  "about you", "decathlon", "obi", "bauhaus", "hornbach", "tchibo", "uniqlo", "c&a", "galeria", "apple",
                  "thalia", "douglas", "kleinanzeigen", "temu", "shein")),
    ("cash", ("geldautomat", "bargeld", "auszahlung", "atm", "ga nr")),
    ("donations", ("spende", "unicef", "ärzte ohne grenzen", "wwf", "greenpeace", "caritas", "diakonie")),
]
NOT_SPENDING = {"income_salary", "income_benefits", "income_other", "investing", "transfer_own"}
LABEL = {
    "housing": "Housing (rent, service charges)", "utilities": "Energy, water, broadcasting fee",
    "telecom": "Phone and internet", "insurance": "Insurance", "subscriptions": "Subscriptions and memberships",
    "children": "Children", "groceries": "Groceries and drugstore", "eating_out": "Eating out and delivery",
    "transport": "Transport and car", "health": "Health", "travel": "Travel", "shopping": "Shopping",
    "cash": "Cash withdrawals", "donations": "Donations", "loan": "Loan and instalment payments",
    "fees_interest": "Bank fees and overdraft interest", "tax": "Tax payments", "other": "Not categorised",
}
# Areas where a household can usually act, with the question to ask about each.
REVIEW_HINTS = {
    "subscriptions": "List every one; cancel what was not used in the last month.",
    "insurance": "Compare against the needs list (Haftpflicht, BU, Risikoleben first); drop duplicates and small-risk cover.",
    "telecom": "Check contract end dates; out-of-contract tariffs are usually dearer than current offers.",
    "utilities": "Compare electricity and gas tariffs once a year.",
    "fees_interest": "Avoidable: move to a free account and clear the overdraft.",
    "eating_out": "Set a monthly amount rather than cutting it out.",
    "shopping": "Largest discretionary block for most households; set a monthly amount.",
    "loan": "Check each rate against the debt order in the plan.",
    "cash": "Untracked; note for one month what it is spent on.",
    "other": "Needs your labels before any conclusion.",
}


def _key_regex(key):
    """Short keywords must stand alone ('etf' must not match 'netflix'); long ones may sit inside a compound."""
    k = key.strip()
    if len(k) > 5:
        return re.escape(k)
    return r"(?<![a-zäöüß0-9])" + re.escape(k) + r"(?![a-zäöüß0-9])"


_RULES_RE = [(cat, re.compile("|".join(_key_regex(k) for k in keys))) for cat, keys in RULES]


def categorise(party, text, amount):
    hay = f" {party} {text} ".lower()
    for cat, rx in _RULES_RE:
        if rx.search(hay):
            if cat.startswith("income") and amount < 0:
                continue
            return cat
    return "income_other" if amount > 0 else "other"


def _norm_party(p, text):
    s = (p or text or "unknown").lower()
    s = re.sub(r"[^a-zäöüß&+ ]", " ", s)
    s = re.sub(r"\b(gmbh|ag|se|kg|co|mbh|ev|e v|sagt danke|europe|deutschland|germany|sarl|inc|ltd)\b", " ", s)
    return " ".join(s.split()[:3]) or "unknown"


def mask(s):
    """Hide account numbers and long digit runs before anything is printed."""
    s = re.sub(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b", "[IBAN]", s or "")
    return re.sub(r"\d{8,}", "[number]", s)


def analyse_spending(tx):
    """tx: list of dicts with date, amount, party, text. Returns a result dict."""
    if not tx:
        raise ValueError("no transactions")
    tx = sorted(tx, key=lambda t: t["date"])
    first, last = tx[0]["date"], tx[-1]["date"]
    months = max(1.0, ((last - first).days + 1) / 30.4375)
    by_cat, by_party = defaultdict(float), defaultdict(list)
    for t in tx:
        t["cat"] = categorise(t["party"], t["text"], t["amount"])
        by_cat[t["cat"]] += t["amount"]          # refunds net against their category
        if t["amount"] < 0 and t["cat"] not in NOT_SPENDING:
            by_party[_norm_party(t["party"], t["text"])].append(t)
    income = {c: v for c, v in by_cat.items() if c.startswith("income") and v > 0}
    spend = {c: -v for c, v in by_cat.items() if c not in NOT_SPENDING and v < 0}
    total_spend = sum(spend.values())
    total_income = sum(income.values())
    saved = -sum(v for c, v in by_cat.items() if c == "investing")
    cats = [{"category": c, "label": LABEL.get(c, c), "monthly": round(v / months, 2), "annual": round(v / months * 12, 2),
             "share": round(v / total_spend, 4) if total_spend else 0.0, "review": REVIEW_HINTS.get(c, "")}
            for c, v in sorted(spend.items(), key=lambda kv: -kv[1])]
    recurring = []
    for party, items in by_party.items():
        ym = {(t["date"].year, t["date"].month) for t in items}
        amts = [-t["amount"] for t in items]
        med = statistics.median(amts)
        if len(ym) >= min(3, max(2, int(months))) and med > 0 and \
                sum(1 for a in amts if abs(a - med) <= 0.05 * med) >= 0.7 * len(amts):
            per_year = len(items) / months * 12
            recurring.append({"payee": mask(party), "category": items[0]["cat"], "typical": round(med, 2),
                              "times_per_year": round(per_year, 1), "annual": round(med * per_year, 2),
                              "last_seen": items[-1]["date"].isoformat()})
    recurring.sort(key=lambda r: -r["annual"])
    one_offs = sorted((t for t in tx if t["amount"] < 0 and t["cat"] not in NOT_SPENDING), key=lambda t: t["amount"])[:8]
    return {
        "period": {"from": first.isoformat(), "to": last.isoformat(), "months": round(months, 2), "transactions": len(tx)},
        "income_monthly": {c: round(v / months, 2) for c, v in income.items()},
        "income_total_monthly": round(total_income / months, 2),
        "spending_total_monthly": round(total_spend / months, 2),
        "into_investments_monthly": round(saved / months, 2),
        "surplus_monthly": round((total_income - total_spend) / months, 2),
        "savings_rate": round((total_income - total_spend) / total_income, 4) if total_income else None,
        "categories": cats,
        "recurring": recurring,
        "recurring_annual_total": round(sum(r["annual"] for r in recurring), 2),
        "largest_payments": [{"date": t["date"].isoformat(), "amount": round(-t["amount"], 2),
                              "payee": mask(t["party"] or t["text"])[:40], "category": t["cat"]} for t in one_offs],
        "uncategorised_share": round(spend.get("other", 0.0) / total_spend, 4) if total_spend else 0.0,
        "caveats": [c for c in (
            "Less than three months of data: one-off payments distort the averages." if months < 2.9 else "",
            "More than 15% of spending is not categorised: label the largest payees before drawing conclusions."
            if total_spend and spend.get("other", 0.0) / total_spend > 0.15 else "",
            "Yearly payments (insurance, holidays) only show if the period covers them; twelve months is best."
            if months < 11.5 else "") if c],
    }


# -------------------------------------------------------------- portfolio
KAPEST = 0.25
SOLI = 0.055
TEILFREISTELLUNG = {"etf_equity": 0.30, "fund_active": 0.30, "etf_mixed": 0.15, "etf_bond": 0.0}
BROAD_KEYS = (("world", ("msci world", "ftse all-world", "all-world", "acwi", "ftse developed", "global all cap",
                         "msci all country")),
              ("usa", ("s&p 500", "s&p500", "nasdaq", "msci usa", "us total")),
              ("europe", ("stoxx europe 600", "msci europe", "euro stoxx")),
              ("germany", ("dax", "mdax", "msci germany")),
              ("em", ("emerging markets", "msci em")))
SINGLE_CAP = 0.05        # one share
STOCKS_CAP = 0.20        # all single shares together
CRYPTO_CAP = 0.10
TER_HIGH = 0.75          # percent a year
TER_CHEAP = 0.20         # benchmark for a broad index fund
REAL_RETURN = 0.04


def tax_rate(church=0.0):
    """Abgeltungsteuer incl. Soli; with church tax the 25% is reduced first."""
    kap = KAPEST / (1 + KAPEST * church) if church else KAPEST
    return kap * (1 + SOLI + church)


def read_holdings(path):
    rows = list(csv.DictReader(io.StringIO(_read_text(path)), delimiter=max(";,\t", key=_read_text(path).splitlines()[0].count)))
    out = []
    for r in rows:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        if not r.get("name"):
            continue
        out.append({"name": r["name"], "isin": r.get("isin", ""), "type": (r.get("type") or "other").lower(),
                    "quantity": parse_amount(r.get("quantity")) or 0.0, "cost": parse_amount(r.get("cost_basis")),
                    "value": parse_amount(r.get("value")) or 0.0, "ter": parse_amount(r.get("ter")),
                    "plan": parse_amount(r.get("monthly_plan")) or 0.0, "bought": parse_date(r.get("bought", ""))})
    return out


def _region(name):
    low = name.lower()
    for region, keys in BROAD_KEYS:
        if any(k in low for k in keys):
            return region
    return None


def analyse_portfolio(holdings, allowance=1000.0, church=0.0, today=None, marginal=0.35):
    today = today or date.today()
    total = sum(h["value"] for h in holdings)
    if total <= 0:
        raise ValueError("portfolio value is zero")
    rate = tax_rate(church)
    stocks = sum(h["value"] for h in holdings if h["type"] == "stock")
    crypto = sum(h["value"] for h in holdings if h["type"] == "crypto")
    # The cheapest fund per region is the one to keep; ties go to the larger position.
    keep = {}
    for h in holdings:
        reg = _region(h["name"]) if h["type"] in ("etf_equity", "fund_active") else None
        h["region"] = reg
        if reg and h["type"] == "etf_equity":
            k = (h["ter"] if h["ter"] is not None else 9.0, -h["value"])
            if reg not in keep or k < keep[reg][0]:
                keep[reg] = (k, h["name"])
    world_or_usa = [h for h in holdings if h.get("region") in ("world", "usa")]
    pos = []
    for h in holdings:
        w = h["value"] / total
        gain = None if h["cost"] is None else h["value"] - h["cost"]
        tf = TEILFREISTELLUNG.get(h["type"], 0.0)
        held_days = (today - h["bought"]).days if h["bought"] else None
        private_sale = h["type"] in ("crypto", "gold")        # § 23 EStG: personal rate, tax-free after a year
        tax_free = private_sale and held_days is not None and held_days > 365 and h["plan"] == 0
        taxable = 0.0 if gain is None or tax_free else gain * (1 - tf)
        tax = max(0.0, taxable) * (marginal if private_sale else rate)
        ter = h["ter"]
        cost_year = None if ter is None else h["value"] * ter / 100
        notes, action = [], "KEEP"
        if h["type"] == "stock" and w > SINGLE_CAP:
            action = "TRIM"
            notes.append(f"Single share at {w:.1%} of the portfolio; guide is {SINGLE_CAP:.0%}. "
                         f"Reducing to the guide means selling about €{h['value'] - SINGLE_CAP * total:,.0f}.")
        if h["type"] == "crypto" and crypto / total > CRYPTO_CAP:
            action = "TRIM"
            notes.append(f"Crypto is {crypto / total:.1%} of the portfolio; guide is at most {CRYPTO_CAP:.0%}.")
        if h["type"] == "fund_active" or (ter is not None and ter >= TER_HIGH):
            action = "REPLACE" if action == "KEEP" else action
            if ter is not None:
                n = 20
                drag = h["value"] * ((1 + REAL_RETURN - TER_CHEAP / 100) ** n - (1 + REAL_RETURN - ter / 100) ** n)
                save_year = h["value"] * (ter - TER_CHEAP) / 100
                notes.append(f"Costs {ter:.2f}% a year (€{cost_year:,.0f}); against a {TER_CHEAP:.2f}% index fund that is "
                             f"about €{drag:,.0f} over {n} years on today's balance.")
                if tax > 0 and save_year > 0:
                    notes.append(f"Switching triggers about €{tax:,.0f} tax; the lower cost earns that back in "
                                 f"about {tax / save_year:.1f} years.")
            else:
                notes.append("Actively managed fund with unknown cost: look up the TER (Basisinformationsblatt).")
        reg = h.get("region")
        if reg and h["type"] == "etf_equity" and keep.get(reg, (None, h["name"]))[1] != h["name"]:
            action = "CONSOLIDATE" if action == "KEEP" else action
            notes.append(f"Overlaps with '{keep[reg][1]}' (same market, cheaper or larger). Stop adding here; "
                         "selling is optional and has a tax cost.")
        elif reg == "usa" and any(x.get("region") == "world" for x in world_or_usa):
            notes.append("A world fund is already about two-thirds US shares; this adds to that weight on purpose or by accident.")
        if h["type"] == "etf_equity" and reg == "world" and action == "KEEP":
            action = "CORE"
            notes.append("Broad, low-cost core holding: the place for new money.")
        if gain is not None and gain < 0 and not tax_free:
            notes.append(f"Unrealised loss of €{-gain:,.0f}: selling books it in the loss pot"
                         + (" (losses on shares only offset gains on shares)." if h["type"] == "stock" else "."))
        if tax_free and gain and gain > 0:
            notes.append("Held more than a year: a sale is tax-free (private sale, § 23 EStG).")
        elif private_sale and gain and gain > 0:
            notes.append(f"Private sale (§ 23 EStG): units held under a year are taxed at your personal rate "
                         f"({marginal:.0%} assumed here, so the tax shown is an upper bound if part is older); "
                         "units held over a year are tax-free. With a running plan, each purchase has its own year. "
                         "A change to the one-year rule for crypto is under discussion: check the current law.")
        plan_note = ""
        if h["plan"] > 0:
            plan_note = {"TRIM": "STOP PLAN", "REPLACE": "STOP PLAN", "CONSOLIDATE": "STOP PLAN"}.get(action, "CONTINUE")
        pos.append({"name": h["name"], "isin": h["isin"], "type": h["type"], "value": round(h["value"], 2),
                    "weight": round(w, 4), "gain": None if gain is None else round(gain, 2),
                    "gain_pct": None if gain is None or not h["cost"] else round(gain / h["cost"], 4),
                    "tax_if_sold_today": round(tax, 2), "ter": ter,
                    "cost_per_year": None if cost_year is None else round(cost_year, 2),
                    "monthly_plan": h["plan"], "plan": plan_note, "action": action, "notes": notes})
    pos.sort(key=lambda p: -p["value"])
    # Gains that fit into the unused allowance, cheapest tax first: fund positions with gains.
    harvest, left = [], allowance
    for p in sorted((p for p in pos if p["gain"] and p["gain"] > 0 and p["type"] in TEILFREISTELLUNG),
                    key=lambda p: (p["action"] not in ("REPLACE", "CONSOLIDATE"), p["gain_pct"] or 0)):
        if left <= 0:
            break
        tf = TEILFREISTELLUNG[p["type"]]
        taxable_total = p["gain"] * (1 - tf)
        share = min(1.0, left / taxable_total)
        harvest.append({"name": p["name"], "sell_value": round(p["value"] * share, 2),
                        "gain_realised": round(p["gain"] * share, 2), "allowance_used": round(taxable_total * share, 2)})
        left -= taxable_total * share
    known = [p for p in pos if p["ter"] is not None]
    plans = sum(p["monthly_plan"] for p in pos)
    stop = sum(p["monthly_plan"] for p in pos if p["plan"] == "STOP PLAN")
    return {
        "total_value": round(total, 2),
        "positions": pos,
        "by_type": {t: round(sum(p["value"] for p in pos if p["type"] == t) / total, 4) for t in sorted({p["type"] for p in pos})},
        "largest_position_weight": pos[0]["weight"],
        "single_shares_weight": round(stocks / total, 4),
        "crypto_weight": round(crypto / total, 4),
        "flags": [f for f in (
            f"Single shares are {stocks / total:.1%} of the portfolio (guide: at most {STOCKS_CAP:.0%})." if stocks / total > STOCKS_CAP else "",
            f"Crypto is {crypto / total:.1%} of the portfolio (guide: at most {CRYPTO_CAP:.0%})." if crypto / total > CRYPTO_CAP else "",
            f"{len(pos)} positions: more than about 8 is hard to keep an eye on and rarely adds diversification." if len(pos) > 8 else "",
            "Purchase values missing for some positions: gains and tax could not be computed for them."
            if any(p["gain"] is None for p in pos) else "") if f],
        "weighted_ter": round(sum(p["value"] * p["ter"] for p in known) / sum(p["value"] for p in known), 3) if known else None,
        "cost_per_year": round(sum(p["cost_per_year"] for p in known), 2),
        "unrealised_gain": round(sum(p["gain"] or 0 for p in pos), 2),
        "tax_if_all_sold": round(sum(p["tax_if_sold_today"] for p in pos), 2),
        "tax_rate_used": round(rate, 5),
        "marginal_rate_assumed_for_private_sales": marginal,
        "allowance_assumed_unused": allowance,
        "allowance_harvest": harvest,
        "plans_monthly_total": round(plans, 2),
        "plans_to_stop_monthly": round(stop, 2),
    }

# ------------------------------------------------------------------- cli


def _print_spending(r):
    p = r["period"]
    print(f"Period {p['from']} to {p['to']} ({p['months']} months, {p['transactions']} transactions)")
    print(f"Income €{r['income_total_monthly']:,.0f}/month | spending €{r['spending_total_monthly']:,.0f}/month | "
          f"into investments €{r['into_investments_monthly']:,.0f}/month | surplus €{r['surplus_monthly']:,.0f}/month")
    print("\nCategory | Monthly | Annual | Share")
    for c in r["categories"]:
        print(f"{c['label']} | €{c['monthly']:,.0f} | €{c['annual']:,.0f} | {c['share']:.1%}")
    print(f"\nRecurring payments (€{r['recurring_annual_total']:,.0f} a year)")
    for x in r["recurring"]:
        print(f"{x['payee']} | {x['category']} | €{x['typical']:,.2f} x {x['times_per_year']} | €{x['annual']:,.0f}/year")
    for c in r["caveats"]:
        print("Note:", c)


def _print_portfolio(r):
    print(f"Portfolio €{r['total_value']:,.0f} | unrealised gain €{r['unrealised_gain']:,.0f} | "
          f"cost €{r['cost_per_year']:,.0f}/year (TER {r['weighted_ter']}%) | tax if all sold €{r['tax_if_all_sold']:,.0f}")
    for p in r["positions"]:
        g = "n/a" if p["gain"] is None else f"€{p['gain']:,.0f}"
        print(f"\n{p['action']:<11} {p['name']} | {p['weight']:.1%} | €{p['value']:,.0f} | gain {g} | "
              f"tax if sold €{p['tax_if_sold_today']:,.0f}" + (f" | plan €{p['monthly_plan']:,.0f}: {p['plan']}" if p["plan"] else ""))
        for n in p["notes"]:
            print("   -", n)
    for f in r["flags"]:
        print("Flag:", f)


def selftest():
    assert parse_amount("1.234,56") == 1234.56 and parse_amount("-12,50 €") == -12.5
    assert parse_amount("12,50-") == -12.5 and parse_amount("1,234.56") == 1234.56
    assert parse_amount("1.234") == 1234.0 and parse_amount("0.125") == 0.125 and parse_amount("45.5") == 45.5
    assert parse_date("03.11.2026") == date(2026, 11, 3) and parse_date("2026-11-03") == date(2026, 11, 3)
    assert categorise("REWE Markt", "", -30) == "groceries" and categorise("ACME GmbH", "Gehalt 10/26", 4000) == "income_salary"
    assert categorise("Trade Republic", "Sparplan", -500) == "investing"
    assert "[IBAN]" in mask("an DE89 3704 0044 0532 0130 00 gesendet")
    tx = []
    for m in (8, 9, 10):
        tx += [{"date": date(2026, m, 1), "amount": 4000.0, "party": "ACME GmbH", "text": "Gehalt"},
               {"date": date(2026, m, 2), "amount": -1200.0, "party": "Hausverwaltung X", "text": "Miete"},
               {"date": date(2026, m, 5), "amount": -13.99, "party": "Netflix", "text": ""},
               {"date": date(2026, m, 9), "amount": -300.0, "party": "REWE", "text": ""},
               {"date": date(2026, m, 15), "amount": -500.0, "party": "Trade Republic", "text": "Sparplan"}]
    tx[-1]["date"] = date(2026, 10, 31)
    r = analyse_spending(tx)
    assert abs(r["period"]["months"] - 3.0) < 0.05, r["period"]
    assert abs(r["spending_total_monthly"] - 1513.99 * 3 / (92 / 30.4375)) < 0.01
    assert abs(r["into_investments_monthly"] - 500 * 3 / (92 / 30.4375)) < 0.01
    assert {x["payee"] for x in r["recurring"]} >= {"netflix", "hausverwaltung x", "rewe"}
    assert abs(tax_rate() - 0.26375) < 1e-9 and abs(tax_rate(0.09) - 0.27995) < 1e-4
    h = [{"name": "MSCI World ETF A", "isin": "X1", "type": "etf_equity", "quantity": 1, "cost": 8000.0, "value": 10000.0,
          "ter": 0.20, "plan": 300.0, "bought": None},
         {"name": "FTSE All-World ETF B", "isin": "X2", "type": "etf_equity", "quantity": 1, "cost": 5000.0, "value": 6000.0,
          "ter": 0.22, "plan": 100.0, "bought": None},
         {"name": "Global Stars Fonds", "isin": "X3", "type": "fund_active", "quantity": 1, "cost": 9000.0, "value": 10000.0,
          "ter": 1.80, "plan": 100.0, "bought": None},
         {"name": "Employer AG", "isin": "X4", "type": "stock", "quantity": 1, "cost": 10000.0, "value": 8000.0,
          "ter": 0.0, "plan": 0.0, "bought": None},
         {"name": "Bitcoin", "isin": "", "type": "crypto", "quantity": 1, "cost": 1000.0, "value": 2000.0,
          "ter": None, "plan": 0.0, "bought": date(2024, 1, 1)}]
    p = analyse_portfolio(h, allowance=1000.0, today=date(2026, 11, 11))
    act = {x["name"]: x for x in p["positions"]}
    assert p["total_value"] == 36000.0
    assert act["MSCI World ETF A"]["action"] == "CORE" and act["MSCI World ETF A"]["plan"] == "CONTINUE"
    assert act["FTSE All-World ETF B"]["action"] == "CONSOLIDATE" and act["FTSE All-World ETF B"]["plan"] == "STOP PLAN"
    assert act["Global Stars Fonds"]["action"] == "REPLACE"
    assert act["Employer AG"]["action"] == "TRIM" and act["Employer AG"]["tax_if_sold_today"] == 0.0
    assert act["Bitcoin"]["tax_if_sold_today"] == 0.0 and act["Bitcoin"]["action"] == "KEEP"
    assert abs(act["MSCI World ETF A"]["tax_if_sold_today"] - 2000 * 0.7 * 0.26375) < 0.01      # 369.25
    assert abs(act["Global Stars Fonds"]["cost_per_year"] - 180.0) < 0.01
    assert p["plans_to_stop_monthly"] == 200.0
    assert abs(sum(x["allowance_used"] for x in p["allowance_harvest"]) - 1000.0) < 0.01
    print("selftest ok")


def _json_default(o):
    return o.isoformat() if isinstance(o, date) else str(o)


if __name__ == "__main__":
    a = sys.argv[1:]
    as_json = "--json" in a

    def opt(name, default):
        return float(a[a.index(name) + 1]) if name in a else default
    files = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in ("--allowance", "--church", "--marginal"))]
    if "--selftest" in a:
        selftest()
    elif files and files[0] == "spending" and len(files) > 1:
        res = analyse_spending([t for f in files[1:] for t in read_transactions(f)])
        print(json.dumps(res, indent=2, ensure_ascii=False, default=_json_default)) if as_json else _print_spending(res)
    elif files and files[0] == "portfolio" and len(files) == 2:
        res = analyse_portfolio(read_holdings(files[1]), allowance=opt("--allowance", 1000.0), church=opt("--church", 0.0),
                                marginal=opt("--marginal", 0.35))
        print(json.dumps(res, indent=2, ensure_ascii=False, default=_json_default)) if as_json else _print_portfolio(res)
    else:
        print(__doc__)
        sys.exit(1)
