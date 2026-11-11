# Wealth Guide Germany

A Claude skill that builds a personal wealth plan for people who are tax resident in Germany. It runs a short interview, checks current figures on the web, does the calculations in code, and writes a 12-section plan in euros under German rules.

> **Educational use only.** This is not Anlageberatung, Steuerberatung or Rechtsberatung. The reference figures in `SKILL.md` were checked on **11 November 2026** and will go out of date. The skill is instructed to re-check time-sensitive figures on every run, but you remain responsible for verifying anything you act on. For decisions that matter, talk to a Steuerberater, a fee-only adviser or the Verbraucherzentrale.

## What it does

1. **Interview** – six short multiple-choice screens: work status, household, goal, income and spending, assets, debt, risk tolerance and insurance. You can type exact figures instead of picking ranges.
2. **Refresh** – looks up the current tax tariff, social insurance ceilings, Basiszins, savings and mortgage rates, and the status of pending laws.
3. **Diagnose** – net income, surplus, savings rate, emergency fund, pension gap and a 0–100 financial health score.
4. **Strategies** – three to five strategies matched to your profile, with euro amounts and a first step each.
5. **Challenge** – stress test (equities −40% plus six months without income), sensitivity checks and a verdict per strategy.
6. **Plan** – summary, current position, three-scenario projections, strategy blueprint, debt, tax and subsidies, monthly money flow, risks, action plan, market context, learning path and key dates.

## What it knows

Income tax and Soli (2026 tariff), social contributions, Abgeltungsteuer, Sparerpauschbetrag, Teilfreistellung and Vorabpauschale, ETF investing with example ISINs, the statutory pension, bAV, Rürup, Riester and the Altersvorsorgedepot starting in 2027, Frühstart-Rente, VL and savings bonuses, property purchase costs by Bundesland, KfW loans, landlord taxation, side income, and gift and inheritance allowances.

## Limits

- Germany only. Cross-border income, expat tax questions and other countries are out of scope.
- Figures are a snapshot. Laws marked as pending in `SKILL.md` (for example the crypto holding-period reform and the 2027 social insurance ceilings) may have changed.
- Fund names are examples of a category, not recommendations. Check current costs before buying anything.
- If you give ranges instead of exact figures, the plan works from midpoints and marks them as estimates.

## Use it in the Claude app

Add the contents of `SKILL.md` as a skill in your Claude account, then say **"wealth guide"**, **"Finanzplan"** or **"Vermögensplan"** in a chat.

## Use it in Claude Code

```bash
git clone https://github.com/aniketsahay/wealth-guide-germany.git
mkdir -p ~/.claude/skills
ln -s "$(pwd)/wealth-guide-germany" ~/.claude/skills/wealth-guide-germany
```

Start Claude Code in any directory and type `wealth guide`. The skill needs web search to refresh figures and a way to run Python for the calculations. Nothing else is installed and nothing is stored: the plan ends with a "Your profile" block you can paste back in next time.

## Updating the figures

Everything time-sensitive is marked ⟳ in `SKILL.md`. At the start of each year, update at least: the § 32a tariff formula and Grundfreibetrag, the Soli threshold, social insurance ceilings and rates, the Basiszins, Rürup and bAV limits, Kindergeld, and the "checked" date. Pull requests with a source link are welcome.

## Credits and licence

The idea and the six-step method come from [caseonix/wealth-guide](https://github.com/caseonix/wealth-guide) by Srivatsa Kasagar (MIT), which covers the US, Canada and India. This version is a rewrite for German rules.

MIT licence, see `LICENSE`.
