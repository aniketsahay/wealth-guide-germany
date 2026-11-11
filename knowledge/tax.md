# Tax (Einkommensteuer) for private households

Headline figures (tax tariff, social insurance values, pension values, subsidies, allowances) were checked against sources on 11 November 2026. Rules of thumb and long-standing legal rules come from general knowledge and should be confirmed before anyone relies on them. Everything with a year in it changes annually: confirm before use.

## How German income tax works

1. Add up income from seven categories (employment, self-employment, business, rental, capital, other, agriculture).
2. Subtract Werbungskosten (costs of earning the income) from each category.
3. Subtract Sonderausgaben (pension and health contributions, church tax, donations, childcare) and außergewöhnliche Belastungen.
4. The result is the zu versteuerndes Einkommen (zvE). The tariff in § 32a EStG is applied to it.
5. Married couples and registered partners can be assessed jointly: the combined zvE is halved, the tariff applied, and the result doubled (Ehegattensplitting). The benefit is largest when incomes are unequal and zero when they are equal.
6. Capital income is normally taxed separately at a flat rate (see `investing.md`).

## Tariff 2026 (Grundtarif)

| zvE | Income tax | Average rate | Marginal rate |
|---:|---:|---:|---:|
| €12,348 | €0 | 0% | 14% begins |
| €15,000 | €436 | 2.9% | 18.9% |
| €20,000 | €1,571 | 7.9% | 24.7% |
| €30,000 | €4,217 | 14.1% | 28.2% |
| €40,000 | €7,210 | 18.0% | 31.7% |
| €50,000 | €10,548 | 21.1% | 35.1% |
| €60,000 | €14,233 | 23.7% | 38.6% |
| €70,000 | €18,264 | 26.1% | 42.0% |
| €100,000 | €30,864 | 30.9% | 42.0% |
| €150,000 | €51,864 | 34.6% | 42.0% |
| €300,000 | €115,530 | 38.5% | 45.0% |

- Grundfreibetrag €12,348 (€24,696 jointly). 42% from €69,879. 45% from €277,826.
- The marginal rate is what matters for every deduction and every pension product: a €1,000 deduction saves €1,000 × marginal rate.
- Exact formula: see the code block in `SKILL.md`.

## Surcharges

- **Solidaritätszuschlag:** 5.5% of income tax, but only when income tax exceeds €20,350 (€40,700 jointly). Above that it phases in at 11.9% of the excess until it reaches the full 5.5%. Always charged on capital gains tax.
- **Kirchensteuer:** 8% of income tax in Bayern and Baden-Württemberg, 9% elsewhere. Deductible as a Sonderausgabe. Leaving the church ends it within a month or two, depending on the Land.

## Tax classes (Steuerklassen)

Tax classes only set the monthly withholding. The annual return fixes the final amount.

| Class | Who |
|---|---|
| I | Single, divorced, widowed |
| II | Single parents (includes the Entlastungsbetrag) |
| III / V | Married: higher earner III, lower earner V |
| IV / IV | Married, similar incomes; "IV with factor" spreads withholding accurately |
| VI | Second and further jobs |

- III/V gives the couple more cash during the year but often a back-payment and a compulsory return. IV with factor avoids both.
- Wage-replacement benefits (Elterngeld, ALG I, Krankengeld, Kurzarbeitergeld) are calculated from net pay, so the person who will claim them should be in the better class early enough. Check the lead times before a birth or a planned job change.

## Deductions employees most often miss

**Werbungskosten** (only help above the automatic €1,230 Arbeitnehmer-Pauschbetrag)
- Commute: €0.38 per km of one-way distance from the first km, per working day at the workplace (since 2026).
- Home office: €6 per day, at most €1,260 a year. Not on the same day as a commute claim unless no other desk is available.
- Work equipment (computer, desk, chair, software, professional books); items up to €800 net are deducted at once.
- Training for the current profession, application costs, job-related moving costs, double household, union and professional association fees.

**Sonderausgaben**
- Pension contributions (statutory pension, Rürup, professional pension schemes) up to the annual cap; see `retirement.md`.
- Basic health and long-term care contributions in full.
- Church tax, donations (up to 20% of income), childcare: 80% of costs, at most €4,800 per child under 14, paid by bank transfer against an invoice.

**Direct tax reductions (§ 35a EStG)** – these cut the tax bill itself, not just income
- Handwerkerleistungen: 20% of labour costs, at most €1,200 a year.
- Haushaltsnahe Dienstleistungen (cleaning, gardening, care, the service part of the Nebenkostenabrechnung): 20%, at most €4,000.
- Minijob in the household: 20%, at most €510.
- Renters qualify too: use the landlord's § 35a statement from the service-charge bill.

**Außergewöhnliche Belastungen:** medical costs above a personal threshold, disability and care allowances, support payments to relatives.

## Children

- Kindergeld €259 per child per month. Alternatively the Kinderfreibetrag including BEA of €9,756 per child for both parents. The tax office picks the better one automatically; the allowance wins only at high incomes.
- Single parents: Entlastungsbetrag (tax class II).
- Children also change long-term care contributions and several subsidies (see `retirement.md`).

## Who must file, and when

- **Compulsory** if, for example: tax classes III/V or IV with factor; more than one employer at once; more than €410 of wage-replacement benefits or of untaxed side income; an allowance entered on the wage tax card; any rental or self-employment income.
- **Voluntary** otherwise, up to four years back. Most employees who file get a refund.
- **Deadline:** 31 July of the following year (next working day if a weekend); about seven months later with a Steuerberater or Lohnsteuerhilfeverein.
- **Tools:** ELSTER is free. Commercial software and Lohnsteuerhilfevereine cost little relative to typical refunds.
- **Lohnsteuerermäßigung:** if large deductions recur every year, have an allowance entered so the refund arrives monthly.

## Special situations

- **Progressionsvorbehalt:** Elterngeld, ALG I, Krankengeld and Kurzarbeitergeld are tax-free but raise the rate on other income. Plan for a back-payment in years with these benefits.
- **Severance pay (Abfindung):** the Fünftelregelung can reduce tax, but since 2025 it is applied only through the tax return, not by the employer.
- **Minijob:** up to €603 a month (2026), flat-taxed by the employer. **Midijob:** from €603.01 to €2,000 with reduced employee social contributions.
- **Rental income:** see `property.md`. **Side business:** see `income-career.md`.
- **Moving to or from Germany, foreign income, foreign accounts:** out of scope; refer to a Steuerberater.

## Yearly tax checklist for employees

1. File a return, and file the last four years if never done.
2. Split the Freistellungsauftrag across banks and brokers so the Sparerpauschbetrag is fully used.
3. Collect § 35a invoices and the landlord's statement.
4. Check the tax-class combination before a planned birth or job change.
5. Use tax-free employer benefits before asking for the same value as gross pay (see `income-career.md`).
6. Decide by early December on pension top-ups that need payment in the same year (Rürup, voluntary statutory contributions, Altersvorsorgedepot from 2027).
7. Request a Verlustbescheinigung by 15 December if losses sit at one bank and gains at another.

## Sources

§ 32a EStG; Solidaritätszuschlaggesetz §§ 3–4; § 35a EStG; BMF Monatsbericht February 2026; Finanztip and Steuertipps overviews of Pauschbeträge 2026.
