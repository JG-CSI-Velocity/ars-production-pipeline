# Transactional Intelligence Engine Operating Model

Browser HTML operating view: [`engine-operating-model.html`](engine-operating-model.html)

The CLI is not the intended user experience. The CLI is the backend runner. The product experience should live inside the existing Velocity UI as an **Intelligence** workflow for CSMs, analysts, and consultants.

## The Human Workflow

```text
Client sends monthly files
  -> CSM stages files
  -> CSM opens Velocity UI
  -> CSM selects CSM / month / client
  -> Engine checks readiness
  -> CSM runs Intelligence
  -> Analyst reviews evidence and flags
  -> Consultant approves the story
  -> CSM exports client package
  -> Campaign/action results feed the next month
```

## Roles

| Role | What they do | What they should see |
|---|---|---|
| CSM | Owns the monthly client run and export package | Run status, file readiness, warnings, client-ready downloads |
| Analyst | Validates data, methods, confidence, and outliers | Feature tables, PFI reasons, quality flags, model diagnostics |
| Consultant | Turns evidence into the recommendation story | Top insights, financial impact, opportunity priority, proof |
| Client team | Acts on the recommendations | Executive brief, action lists, campaign plays, measurement plan |

## UI Experience

The existing UI should get a new top-level **Intelligence** tab.

### 1. Select Run

The user selects:

- CSM.
- Month.
- Client.
- Product mode: `ARS`, `TXN`, `Combined`, or `Intelligence`.

The UI should reuse the existing folder-based client discovery.

### 2. Readiness Check

Before running analysis, the UI shows:

| Readiness area | What appears |
|---|---|
| Files found | ODD, TXN files, modified extracts, campaign files, deferred/workbook side files |
| Layout status | Known contract, unknown layout, missing required fields |
| Account matching | Expected matchability between ODD accounts and transactions |
| History depth | Number of months available |
| Confidence | Green/yellow/red readiness score |

The CSM should know whether the run is clean before waiting on analysis.

### 3. Run Intelligence

The button should say:

```text
Run Intelligence Engine
```

Behind the scenes it calls the Python engine, not the user.

The run writes to:

```text
01_Analysis/01_Completed_Intelligence/<CSM>/<month>/<client_id>/
```

### 4. Review Intelligence

After the run, the UI should show five review surfaces:

| Review surface | User question |
|---|---|
| Data Trust | Can we trust this month's data? |
| PFI / Relationship | Who owns the relationship? |
| Counterparty Intelligence | Which employers, external FIs, lenders, and merchants explain behavior? |
| Relationship Segments | What financial-life pattern explains the account behavior? |
| Executive Scorecard | What is healthy, risky, or ready for action? |
| Strategy Roadmap | What should we do now, next, and later? |
| Opportunity Portfolio | Where is the value or risk? |
| Action Lists | Who should the client target? |
| Measurement | How will we prove whether it worked? |

### 5. Export Package

The CSM should download:

| File | Audience | Purpose |
|---|---|---|
| `executive_brief.html` or `.pptx` | Client executives | The story and top decisions |
| `transactional_intelligence_package.xlsx` | CSM / analyst / consultant | Reviewable story, handoffs, opportunities, PFI, targets, and outcomes |
| `intake_work_order.csv` | Analyst / data team | File-by-file decisioning for received client extracts |
| `role_handoffs.csv` | Owner / CSM / analyst / marketing / data team | Who owns each decision, which export they use, and what they do next |
| `campaign_targets.csv` | Client marketing / branch teams | Named target lists, reason codes, and measurement group |
| `data_quality_report.html` | Internal / analyst | Confidence, coverage, warnings |
| `counterparty_summary.csv` | CSM / analyst / consultant | Top payroll, external FI, lender, and merchant relationships by amount and account reach |
| `counterparty_signals.csv` | Analyst / data team | Account-level counterparty graph for deeper investigation or Snowflake/API use |
| `relationship_segments.csv` | Analyst / consultant / product | Account-level financial-life segment, risk, and next-best motion |
| `segment_summary.csv` | CSM / consultant | Segment-level strategy rollup |
| `executive_scorecard.csv` | Executive / CSM / consultant | RAG strategy health across trust, primacy, risk, activation, economics, measurement, and outcomes |
| `strategy_roadmap.csv` | CSM / marketing / client team | Now/Next/Later execution priorities with proof metrics |
| `pfi_verdicts.csv` | Analyst / data team | Account-level PFI outputs |
| `consulting_story.json` | Product / UI / API | Reusable executive summary, story arc, top plays, and analyst notes |
| `insights.json` | Product / Snowflake / API | Structured insight registry |

## The Output

The engine output is not one file. It is a package.

```text
Completed Intelligence Package

1. Data trust report
2. File intake work order
3. PFI and relationship scorecard
4. Counterparty intelligence
5. Relationship segment rollup
6. Executive scorecard
7. Strategy roadmap
8. Opportunity portfolio
9. Insight registry
10. Action lists
11. Measurement plan
12. Role handoff map
13. Executive consulting brief
14. Consulting story JSON
```

## The Analysis

The analysis should be organized by decision, not by section name.

| Decision area | Engine analysis |
|---|---|
| Data trust | File completeness, layout coverage, account matching, transaction history, confidence |
| Customer financial life | Payroll, spend, external FI movement, obligations, merchant/category behavior |
| Relationship ownership | PFI verdict, split-wallet behavior, competitor-primary accounts, thin relationships |
| Counterparty strategy | Payroll processors, external banks/CUs, lenders, fintechs, merchants, recurrence, direction, and amount |
| Segment strategy | Primary payroll, split-wallet, conversion, activation, dormancy, and external-financial-service groups |
| Executive strategy | Data trust, primacy posture, competitive risk, activation upside, retention risk, economics, measurement readiness, outcomes |
| Value and risk | Revenue leakage, deposit flight, attrition risk, interchange opportunity, Reg E opportunity |
| Growth actions | Payroll conversion, debit activation, relationship expansion, competitor win-back |
| Measurement | Control group, lift, persistence, retained value, revenue outcome |

## The Story

The consulting story should follow this pattern for every client:

```text
1. Can we trust the data?
2. What does the customer base look like?
3. Who owns the relationship today?
4. Where is money leaving or value leaking?
5. Which opportunities are worth acting on first?
6. Who exactly should the client target?
7. How will we measure whether the action worked?
```

## The Consulting Object

Each material insight should be written in this form:

```text
Situation: What population are we looking at?
Finding: What did the engine detect?
Implication: Why does it matter financially or strategically?
Action: What should the institution do next?
Proof: Which data, model, section, and confidence level support this?
```

Example:

```text
Situation: 18,642 active checking households have transaction history.
Finding: 1,842 show payroll or recurring financial activity outside the institution.
Implication: These households are more likely to be split or competitor-primary relationships.
Action: Target the highest-confidence households with a direct-deposit conversion play.
Proof: Payroll detection, external FI tagging, balance profile, transaction history, PFI reason codes.
```

## What Exists Now

The first code layer exists:

```text
01_Analysis/00-Scripts/ars_engine/intelligence/
```

It can produce:

- `file_ledger.csv`
- `data_quality.json`
- `account_month_features.csv`
- `pfi_verdicts.csv`
- `opportunities.csv`
- `intake_work_order.csv`
- `campaign_targets.csv`
- `role_handoffs.csv`
- `consulting_story.json`
- `insights.json`
- `run_summary.json`

## Browser Wiring

| Surface | Status |
|---|---|
| `/api/intelligence/run` | Runs the V1 engine from staged ODD/transaction files |
| `/api/intelligence/outputs/{csm}/{month}/{client_id}` | Returns the package files plus story, handoffs, actions, targets, and outcomes |
| Intelligence tab | Provides readiness, run control, consulting story, action plan, measured outcomes, operating handoff, and downloads |
| Excel export | Packages business-facing sheets for users who do not want raw CSV/JSON |

That is how the engine becomes usable by CSMs and analysts without CLI work.
