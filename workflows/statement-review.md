# Workflow: statement review

For anyone who wants the plan built on real account data instead of estimates. Optional; the plan also works from the interview alone.

## What to collect

| Document | Where to get it | Period |
|---|---|---|
| Girokonto transactions | Online banking: Umsätze → Export → CSV | 12 months is best, 3 at least |
| Credit-card transactions | Card portal or app: export as CSV | Same period |
| Depot overview with purchase values | Broker: Depotübersicht or Depotauszug, as CSV or PDF | Today |
| Savings plans | Broker: Sparplan overview (screenshot is fine) | Today |
| Payslip | Latest Gehaltsabrechnung, one per earner | Last month |
| Pension | Renteninformation; yearly statements for bAV, Riester, Rürup, policies | Latest |
| Loans | Loan or mortgage statement | Latest |
| Tax | Last Steuerbescheid; Jahressteuerbescheinigung from each bank | Last year |

CSV beats PDF: nothing has to be read off a page, so nothing gets misread. Black out anything you would rather not share; names and account numbers are not needed.

## Step 1: read the files
1. CSV exports from German banks are read as they are (semicolon-separated, German number format, lines above the header are skipped).
2. PDFs and screenshots are first copied into a simple table: `date,amount,counterparty,description` for transactions, and `name,isin,type,quantity,cost_basis,value,ter,monthly_plan,bought` for holdings.
3. Check the copy: opening balance plus all transactions must equal the closing balance; positions must add up to the Depot total.

## Step 2: run the analysis
```bash
python3 scripts/statements.py spending giro.csv card.csv
python3 scripts/statements.py portfolio holdings.csv --allowance 2000 --marginal 0.42
```
`--allowance` is the unused Sparerpauschbetrag for the year (€1,000 single, €2,000 joint, minus what the banks have already used). `--marginal` is the personal tax rate used for crypto or gold sold within a year. Add `--church 0.09` (0.08 in Bayern and Baden-Württemberg) if church tax applies, and `--json` for output the calculator can reuse.

Sample files with invented data are in `examples/sample-statements/`.

## Step 3: check what the code could not know
- Label the largest payees in "Not categorised" (PayPal and credit-card settlements hide what was bought).
- Name the accounts that are missing: other banks, the partner's accounts, cash, a second Depot.
- Mark employer shares; the code cannot tell them from any other share.
- One-off payments in the period (a holiday, a new kitchen) are not habits; say which ones were exceptional.

## Step 4: spending
1. Read the category table as monthly averages, not as a budget to feel bad about.
2. Go through the recurring payments one by one: still used? Twice in the household? Cheaper elsewhere?
3. Order of places to look: bank fees and overdraft interest, unused subscriptions, energy and phone contracts past their minimum term, duplicate or low-value insurance, then the discretionary categories you yourself think are too high.
4. For each saving, set up the same amount as an additional standing order into the savings plan on the same day. A saving that stays in the Girokonto gets spent.

## Step 5: holdings
Each position gets one label:

| Label | Meaning | What to do |
|---|---|---|
| CORE | Broad, low-cost world equity ETF | New money goes here |
| KEEP | Nothing speaks against it | Nothing |
| CONSOLIDATE | Second fund for the same market | Stop the savings plan; selling is optional |
| REPLACE | Active fund or TER of 0.75% or more | Compare the tax of switching with the yearly cost saved |
| TRIM | One share above 5%, all shares above 20%, crypto above 10% of the portfolio | Reduce towards the guide, cheapest tax first |

Order of steps, cheapest first:
1. Stop or redirect savings plans. This costs no tax.
2. Use the unused Sparerpauschbetrag: sell and rebuy gains up to the allowance, or use it for the first switches.
3. Realise losses where a position is to go anyway; they sit in the loss pot and offset later gains (losses on shares only against gains on shares).
4. Taxable sales last, and only where the review supports them: a switch out of an expensive fund that pays back within about five years, or a concentration that is a real risk to the household.

## What this review does not do
It does not say whether a company's shares will rise or fall, and it does not time the market. The labels come from cost, overlap, concentration and tax. A single share inside the guides is your decision.

## Privacy
The files are analysed in the session and nothing from them goes into a web search. The script masks IBANs and long numbers in its output. The plan names merchants but no account numbers and no private persons.
