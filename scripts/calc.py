#!/usr/bin/env python3
"""Calculator for Wealth Guide Germany. Standard library only.

Usage:
    python3 calc.py profile.json          # prints a JSON result block
    python3 calc.py --selftest            # runs built-in checks

Every statutory figure lives in YEAR below. Update that block once a year
(and the matching "Reference figures" section in SKILL.md).
"""
import json
import sys

YEAR = {
    "year": 2026,
    # Income tax, § 32a EStG
    "grundfreibetrag": 12348,
    "zone2_end": 17799,
    "zone3_end": 69878,
    "zone4_end": 277825,
    "z2": (914.51, 1400.0),
    "z3": (173.10, 2397.0, 1034.87),
    "z4": (0.42, 11135.63),
    "z5": (0.45, 19470.38),
    # Solidaritätszuschlag
    "soli_rate": 0.055,
    "soli_free_single": 20350,
    "soli_phase_in": 0.119,
    # Social insurance (annual ceilings, employee shares)
    "bbg_pension": 101400,
    "bbg_health": 69750,
    "rv_employee": 0.093,
    "av_employee": 0.013,
    "kv_employee_base": 0.073,
    "kv_zusatz_avg": 0.029,
    "pv_employee": 0.018,
    "pv_childless_extra": 0.006,
    "pv_child_discount": 0.0025,   # per child, 2nd to 5th child under 25
    # Allowances
    "arbeitnehmer_pauschbetrag": 1230,
    "sonderausgaben_pauschbetrag": 36,
    "kindergeld_month": 259,
    "kinderfreibetrag_total": 9756,
    "sparerpauschbetrag": 1000,
    # Capital income
    "abgeltung": 0.25,
    "teilfreistellung_equity": 0.30,
    "basiszins": 0.032,
    # Altersvorsorgedepot (from 2027)
    "avd_tier1_cap": 360, "avd_tier1_rate": 0.50,
    "avd_tier2_cap": 1800, "avd_tier2_rate": 0.25,
    "avd_child_cap": 300, "avd_min_contribution": 120, "avd_starter_bonus": 200,
    # bAV
    "bav_sv_free_share": 0.04, "bav_tax_free_share": 0.08,
}


def est(zve, y=YEAR):
    """Income tax, Grundtarif."""
    x = int(zve)
    if x <= y["grundfreibetrag"]:
        return 0.0
    if x <= y["zone2_end"]:
        v = (x - y["grundfreibetrag"]) / 10000
        a, b = y["z2"]
        return (a * v + b) * v
    if x <= y["zone3_end"]:
        v = (x - y["zone2_end"]) / 10000
        a, b, c = y["z3"]
        return (a * v + b) * v + c
    if x <= y["zone4_end"]:
        r, d = y["z4"]
        return r * x - d
    r, d = y["z5"]
    return r * x - d


def income_tax(zve, joint=False, y=YEAR):
    """Splitting: halve, compute, double."""
    return 2 * est(zve / 2, y) if joint else est(zve, y)


def soli(tax, joint=False, y=YEAR):
    free = y["soli_free_single"] * (2 if joint else 1)
    if tax <= free:
        return 0.0
    return min(y["soli_rate"] * tax, y["soli_phase_in"] * (tax - free))


def marginal_rate(zve, joint=False, y=YEAR):
    return income_tax(zve + 100, joint, y) / 100 - income_tax(zve, joint, y) / 100


def net_estimate(gross, joint=False, children=0, childless_over_23=None,
                 church_rate=0.0, kv_zusatz=None, y=YEAR):
    """Rough annual net for ONE statutory-insured employee. An estimate only:
    use the user's real net figure whenever they have it."""
    if childless_over_23 is None:
        childless_over_23 = children == 0
    zus = y["kv_zusatz_avg"] if kv_zusatz is None else kv_zusatz
    p_base = min(gross, y["bbg_pension"])
    h_base = min(gross, y["bbg_health"])
    rv = y["rv_employee"] * p_base
    av = y["av_employee"] * p_base
    kv = (y["kv_employee_base"] + zus / 2) * h_base
    pv_rate = y["pv_employee"]
    if childless_over_23:
        pv_rate += y["pv_childless_extra"]
    elif children >= 2:
        pv_rate -= y["pv_child_discount"] * (min(children, 5) - 1)
    pv = pv_rate * h_base
    zve = max(0.0, gross - y["arbeitnehmer_pauschbetrag"] - y["sonderausgaben_pauschbetrag"]
              - rv - 0.96 * kv - pv)
    tax = income_tax(zve, joint, y)
    kindergeld = children * y["kindergeld_month"] * 12
    # Günstigerprüfung: Kinderfreibetrag only if the tax saving beats Kindergeld
    if children:
        tax_kfb = income_tax(max(0.0, zve - children * y["kinderfreibetrag_total"]), joint, y)
        if tax - tax_kfb > kindergeld:
            tax, kindergeld = tax_kfb, 0.0
    sol = soli(tax, joint, y)
    church = church_rate * tax
    net = gross - rv - av - kv - pv - tax - sol - church
    return {
        "gross": round(gross), "taxable_income": round(zve),
        "income_tax": round(tax), "soli": round(sol), "church_tax": round(church),
        "social": round(rv + av + kv + pv),
        "net_year": round(net), "net_month": round(net / 12),
        "kindergeld_year": round(kindergeld),
        "marginal_rate": round(marginal_rate(zve, joint, y), 3),
        "note": "estimate; excludes Kindergeld, second earner and all individual deductions",
    }


def _interp(v, pts):
    """Piecewise-linear score from sorted (value, points) anchors."""
    if v <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if v <= x1:
            return y0 + (y1 - y0) * (v - x0) / (x1 - x0)
    return pts[-1][1]


def health_score(net_month, spending_month, cash, consumer_debt, invested,
                 gross_year, age, has_haftpflicht, needs_bu, has_bu,
                 needs_risikoleben, has_risikoleben, pension_gap_covered=False):
    surplus = net_month - spending_month
    months = cash / spending_month if spending_month else 0
    rate = surplus / net_month if net_month else 0
    ef = _interp(months, [(1, 0), (3, 18), (6, 25)])
    sr = _interp(rate, [(0, 0), (0.10, 15), (0.20, 25)])
    debt = _interp(consumer_debt / net_month if net_month else 9, [(0, 20), (1, 0)])
    target = _interp(age, [(25, 0.2), (35, 1), (45, 3), (55, 6), (65, 8)])
    ratio = invested / gross_year / target if gross_year and target else 0
    ret = 15 if pension_gap_covered else _interp(ratio, [(0, 0), (1, 15)])
    prot = 0
    if has_haftpflicht:
        prot = 7
        prot += 5 if (has_bu or not needs_bu) else 0
        prot += 3 if (has_risikoleben or not needs_risikoleben) else 0
    comps = [
        {"label": "Emergency fund", "points": round(ef), "max": 25},
        {"label": "Savings rate", "points": round(sr), "max": 25},
        {"label": "Consumer debt", "points": round(debt), "max": 20},
        {"label": "Retirement track", "points": round(ret), "max": 15},
        {"label": "Protection", "points": round(prot), "max": 15},
    ]
    total = sum(c["points"] for c in comps)
    band = "foundations first" if total < 50 else "building" if total <= 75 else "optimising"
    return {"total": total, "band": band, "components": comps,
            "surplus_month": round(surplus), "savings_rate": round(rate, 3),
            "emergency_months": round(months, 1)}


def project(start, monthly, years, equity_share=1.0, start_year=None,
            equity_real=(0.02, 0.04, 0.06), safe_real=0.005):
    """Year-end balances in today's euros for three real-return scenarios."""
    out = {"years": [], "conservative": [], "base": [], "optimistic": []}
    names = ["conservative", "base", "optimistic"]
    bal = [float(start)] * 3
    y0 = start_year or YEAR["year"]
    out["years"].append(y0)
    for n, b in zip(names, bal):
        out[n].append(round(b))
    for i in range(1, years + 1):
        for k, r in enumerate(equity_real):
            rr = equity_share * r + (1 - equity_share) * safe_real
            bal[k] = bal[k] * (1 + rr) + 12 * monthly * (1 + rr / 2)
            out[names[k]].append(round(bal[k]))
        out["years"].append(y0 + i)
    return out


def loan_payoff(balance, rate, payment_month):
    """Months to clear a loan and total interest. None if the payment is too low."""
    r = rate / 12
    if payment_month <= balance * r:
        return None
    months, interest = 0, 0.0
    while balance > 0.005 and months < 1200:
        i = balance * r
        interest += i
        balance = balance + i - payment_month
        months += 1
    return {"months": months, "interest": round(interest)}


def annuity_payment(principal, rate, initial_repayment):
    """Monthly mortgage payment from interest rate and initial repayment rate."""
    return principal * (rate + initial_repayment) / 12


def avd_subsidy(contribution, children=0, first_year_under_25=False, y=YEAR):
    """Altersvorsorgedepot subsidy per year (rules from 2027)."""
    if contribution < y["avd_min_contribution"]:
        return 0.0
    t1 = min(contribution, y["avd_tier1_cap"]) * y["avd_tier1_rate"]
    t2 = max(0.0, min(contribution, y["avd_tier2_cap"]) - y["avd_tier1_cap"]) * y["avd_tier2_rate"]
    child = children * min(contribution, y["avd_child_cap"])
    bonus = y["avd_starter_bonus"] if first_year_under_25 else 0
    return t1 + t2 + child + bonus


def vorabpauschale_tax(value_jan, gain, distributions=0.0, church_rate=0.0,
                       allowance_left=0.0, y=YEAR):
    """Tax due on an accumulating equity ETF for one year."""
    base = max(0.0, min(value_jan * y["basiszins"] * 0.7, gain) - distributions)
    taxable = max(0.0, base * (1 - y["teilfreistellung_equity"]) - allowance_left)
    rate = y["abgeltung"] * (1 + y["soli_rate"] + church_rate)
    return {"vorabpauschale": round(base, 2), "taxable": round(taxable, 2),
            "tax": round(taxable * rate, 2)}


def bav_limits(y=YEAR):
    return {"sv_and_tax_free_year": y["bav_sv_free_share"] * y["bbg_pension"],
            "tax_free_year": y["bav_tax_free_share"] * y["bbg_pension"]}


def run(profile):
    """profile: dict with the interview answers. Missing keys fall back to None."""
    p = profile
    joint = bool(p.get("joint"))
    res = {"year": YEAR["year"]}
    if p.get("net_month") is None and p.get("gross_year"):
        res["net_estimate"] = net_estimate(
            p["gross_year"], joint, p.get("children", 0),
            church_rate=p.get("church_rate", 0.0), kv_zusatz=p.get("kv_zusatz"))
        net_month = res["net_estimate"]["net_month"]
    else:
        net_month = p.get("net_month", 0)
    debts = p.get("debts", [])
    consumer = sum(d["balance"] for d in debts if d.get("type") != "mortgage")
    res["health_score"] = health_score(
        net_month, p.get("spending_month", 0), p.get("cash", 0), consumer,
        p.get("investments", 0), p.get("gross_year", 0), p.get("age", 35),
        p.get("has_haftpflicht", False), p.get("needs_bu", True), p.get("has_bu", False),
        p.get("needs_risikoleben", False), p.get("has_risikoleben", False),
        p.get("pension_gap_covered", False))
    mortgage = sum(d["balance"] for d in debts if d.get("type") == "mortgage")
    res["net_worth"] = round(p.get("cash", 0) + p.get("investments", 0)
                             + p.get("property_value", 0) - mortgage - consumer)
    res["projection"] = project(
        p.get("investments", 0), p.get("invest_month", max(0, res["health_score"]["surplus_month"])),
        p.get("horizon_years", 15), p.get("equity_share", 0.7))
    res["debts"] = [dict(d, payoff=loan_payoff(d["balance"], d["rate"], d["payment_month"]))
                    for d in debts if d.get("payment_month")]
    res["bav_limits"] = bav_limits()
    return res


def selftest():
    assert abs(est(50000) - 10548.33) < 0.01, est(50000)
    assert est(12348) == 0 and est(12349) > 0
    for b in (17799, 69878, 277825):
        assert abs(est(b + 1) - est(b)) < 1, b            # tariff is continuous
    assert abs(income_tax(100000, True) - 2 * est(50000)) < 0.01
    assert soli(20350) == 0 and abs(soli(21000) - 77.35) < 0.01
    assert abs(soli(60000) - 3300) < 0.01
    assert avd_subsidy(1800) == 540 and avd_subsidy(300, children=1) == 450
    assert avd_subsidy(100, children=2) == 0
    assert bav_limits()["sv_and_tax_free_year"] == 4056.0
    v = vorabpauschale_tax(10000, 800)
    assert v["vorabpauschale"] == 224.0, v
    n = net_estimate(60000)
    assert 3000 < n["net_month"] < 3250, n
    pr = project(10000, 500, 10)
    assert pr["conservative"][-1] < pr["base"][-1] < pr["optimistic"][-1]
    assert len(pr["years"]) == 11
    lp = loan_payoff(10000, 0.12, 500)
    assert lp and 21 <= lp["months"] <= 23, lp
    assert loan_payoff(10000, 0.12, 50) is None
    hs = health_score(3500, 2500, 15000, 0, 40000, 60000, 35, True, True, True, False, False)
    assert hs["total"] == sum(c["points"] for c in hs["components"]) and hs["total"] > 75, hs
    print("selftest ok")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    elif len(sys.argv) == 2:
        with open(sys.argv[1], encoding="utf-8") as f:
            print(json.dumps(run(json.load(f)), indent=2, ensure_ascii=False))
    else:
        print(__doc__)
        sys.exit(1)
