# Client Deck Plan — 3-Story Structure

**Date:** 2026-04-27
**Owner:** JG / CSM team
**Status:** Proposed
**Manifest:** `docs/deck/slide_manifest.json`

Compresses the current ~70-slide combined output into a focused **<40 slide** client-facing deck organized around three critical stories, with conditional ICS insertion and a separate supplementary deck for analyst-level detail.

---

## The 3 Critical Stories

1. **ARS Performance** — did the program work, what did it return
2. **Competition** — who is taking your members' wallet
3. **Financial Services Leakage** — where member dollars flow to other FIs

**ICS** — inserted as its own mini-section between Story 1 and Story 2 **only when ICS data is present** in the client's ODD.

Everything else (demographics, age bands, hourly heatmaps, MCC deep-dives, balance bands, full branch scorecards, deposits, account age curves, etc.) is **window dressing** for the client conversation and moves to a separate supplementary deck.

---

## Slide Manifest

**32 slides without ICS / 38 with ICS.** Both under the 40-slide cap.

| # | Slide | Source modules | Layout |
|---|---|---|---|
| 1 | Title | — | 18 (ARS) |
| 2 | What we'll cover | — | 12 |
| 3 | Executive scorecard (RAG, 6 KPIs) | `executive` + `insights.synthesis` | 8 |
| **4** | **Section divider — ARS Performance** | — | 4 |
| 5 | Hero: Eligible → Mailed → Responded funnel + lift $ | `mailer.insights` + `mailer.reach` + `value.analysis` | 2 |
| 6 | DCTR: % of eligible actively swiping (12-mo trend) | `dctr.penetration` + `dctr.trends` combined | 2 |
| 7 | Reg E opt-in + OD revenue at stake | `rege.status` | 9 |
| 8 | Response rate by wave | `mailer.response` | 2 |
| 9 | Responder vs non-responder spend lift (DID) | `mailer.impact` | 9 |
| 10 | Cohort persistence — do responders stay activated | `mailer.cohort` | 2 |
| 11 | ROI: $ interchange per $1 mail spend | `insights.effectiveness` | 2 |
| 12 | Attrition impact — $ lost from closed accounts | `attrition.impact` | 2 |
| 13 | Dormant accounts — recoverable interchange | `insights.dormant` | 2 |
| 14 | So what: 3 ARS performance moves | `insights.conclusions` (ARS filter) | 12 |
| **15** | *(ICS divider — conditional)* | — | 4 |
| 16 | *ICS: penetration + revenue impact (combined hero)* | `ics.overview` + `ics.revenue_impact` | 2 |
| 17 | *ICS: branch + product + tenure (3-panel)* | `ics.branch` + `ics.product_mix` + `ics.tenure` | 9 |
| 18 | *ICS: referral opportunity* | `ics.referral_intelligence` | 2 |
| 19 | *So what: ICS growth play* | `insights.conclusions` (ICS filter) | 12 |
| **20** | **Section divider — Competition** | — | 4 |
| 21 | Hero: Wallet share — your share vs competitors | `competition.wallet_share` | 2 |
| 22 | Competitor threat quadrant (frequency × spend) | `competition.threat_quadrant` | 8 |
| 23 | Top competitors — annualized $ leaving | `competition.detection` | 2 |
| 24 | Where the wallet goes (top external merchants) | `merchant.top20` (trimmed to 10, external-only) | 2 |
| 25 | So what: 3 wallet-recapture plays | `insights.conclusions` (competition filter) | 12 |
| **26** | **Section divider — Financial Services Leakage** | — | 4 |
| 27 | Hero: $ flowing to other FIs monthly + annualized | `financial_services.fi_transactions` | 2 |
| 28 | Leakage by destination FI (top 10) | `financial_services.leakage` | 2 |
| 29 | Leakage by member segment (who's leaving most) | `financial_services` × `general.engagement_data` | 9 |
| 30 | Trend: is leakage growing or stabilizing | `financial_services` (monthly) | 2 |
| 31 | So what: 3 leakage-stop plays | `insights.conclusions` (FS filter) | 12 |
| **32** | **Section divider — Recommendations** | — | 4 |
| 33 | Top 3 priorities (one per story) | `executive.priorities` | 12 |
| 34 | $ opportunity stack (waterfall: ARS + ICS + competition + FS) | new `executive.opportunity_stack` | 2 |
| 35 | What we need from you | new — synthesis | 12 |
| 36 | Thank you / contact | — | 0 |
| **37** | **Appendix divider** | — | 6 (gray) |
| 38 | Methodology / denominator framework | doc | 12 |
| 39 | Pointer to supplementary deck | — | 12 |

**Without ICS:** omit slides 15-19, renumber → 32 slides.
**With ICS:** 38 slides.

---

## Conditional ICS Insertion

```python
ics_present = (
    ctx.results.get('ics.overview') is not None
    and ctx.results['ics.overview'].kpis.get('n_ics_accounts', 0) > 0
)
manifest = MANIFEST_BASE if not ics_present else insert_ics_section(MANIFEST_BASE)
```

Manifest lives at `02_Presentations/slide_manifest.json` with section tags so ICS can slot in/out without manual renumbering.

---

## What Moves to Supplementary Deck

Separate file: `{client_id}_{month}_supplementary.pptx`. Built via extension of `run_sampler.py` that reads the **inverse** of the main manifest — every chart that ran but isn't in the 32/38-slide deck.

**Contents:**
- All overview slides except eligibility (folded into hero slide 5)
- All branch breakouts beyond top/bottom (DCTR branches, Reg E branches, attrition by branch, branch scorecards)
- All demographic / age-band / business-vs-personal splits
- Full merchant top-50, MCC top-50, MCC by age / engagement / business / seasonal / diversity
- Hourly heatmaps, seasonal patterns, lifecycle, account age curves
- All campaign cohort deep-detail (segment cohort, swipe migration, spend persistence, counterfactual, what-if, slope proof)
- Transaction type splits, balance bands, PFI scoring
- Deposits deck (8 slides) — appended only if requested by CSM
- Full attrition dimensions (only `attrition.impact` survives in main deck)

Audience: client-side analyst who wants to dig. Not presented live.

---

## Compression Techniques Applied

| Technique | Where | Slides saved |
|---|---|---|
| Combine modules into hero slide | Eligibility + DCTR penetration → slide 5; Mailed + Reach + Value → slide 5; Wallet + concentration → slide 21 | ~5 |
| Filter, don't show all | Top 10 merchants instead of top 20; top/bottom branches only | ~3 |
| Two-content layout for adjacent metrics | Reg E status + OD revenue (slide 7); Responder lift (slide 9); Leakage by segment (slide 29) | ~3 |
| One "So what" per story | Slides 14, 19, 25, 31 replace per-module insights slides | ~3 |
| Move reference detail to appendix | Methodology, full branch scorecard | ~2 |
| Spin off supplementary deck | All MCC / merchant / cohort / demographics detail | ~25 |

---

## Implementation Plan

1. **`02_Presentations/slide_manifest.json`** — single source of truth listing the 32/38 slide IDs in order, with combined-module rules and section tags.
2. **`runner.py --mode=client`** — reads the manifest, emits only manifested slides. Default mode stays `full`.
3. **`runner.py --mode=supplementary`** — emits everything NOT in the manifest, into a separate `.pptx`.
4. **3 new combined-hero modules** in `analytics/executive/`:
   - `executive.ars_hero` (eligibility + mailer reach + value)
   - `executive.competition_hero` (wallet share + concentration)
   - `executive.opportunity_stack` (waterfall summing all 4 story-level $ opportunities)
5. **4 "So what" templates** (slides 14, 19, 25, 31) — driven by `insights.synthesis` filtered by story tag.
6. **ICS conditional insert** — manifest plumbing in `runner.py`.

**Effort:** ~2 days. No new chart types beyond the opportunity-stack waterfall. Existing chart code reused.

---

## Open Questions

1. Are these 3 stories right for the **typical CSI client**, or do some clients lean deposits-heavy? (Current plan: deposits = supplementary unless CSM requests promotion.)
2. Defendable $ opportunities on every slide — or do some clients push back on assumptions? (If pushback risk, dollarize only on hero slides 5, 21, 27, 34, and put assumptions on appendix slide 38.)
3. Per-client or per-CSM template? (Recommend per-CSM with client-specific narration so the CSM presents from one consistent structure.)

---

## Dependencies on Audit Findings

This deck plan **assumes the TXN denominator fix from `Analysis Audit 4-27.md` Entry 1 ships first**. Without it:
- Slide 5 hero numbers (eligibility from ARS, reach from TXN-side mailer) will use mismatched bases
- Slide 21 (wallet share) uses `merchant_concentration` which currently lacks eligible filtering
- Slide 27 (FI leakage) uses `financial_services` which currently operates on raw `combined_df`

**Do not present this deck to a client until denominator parity is verified across ARS and TXN modules.**
