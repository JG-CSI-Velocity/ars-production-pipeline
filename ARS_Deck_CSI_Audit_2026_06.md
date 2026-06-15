# CSI PowerPoint Audit — ARS Deck
**Client:** First Central CU  
**File:** `1759_2026_06_ars_deck.pptx`  
**Deck:** Account Revenue Solution | June 2026  
**Total Slides:** 167  
**Audit Date:** June 2026  
**Mode:** Audit + Fix Plan  

---

## Executive Summary

The deck is structurally sound and largely brand-compliant. The CSI 2024 brand color scheme (`#00274C` Navy, `#F15D22` Orange, `#EB2A2E` Red, `#F8971D` Gold) is correctly embedded in the theme. Fonts are properly defined as Montserrat ExtraBold (headings) and Montserrat (body). Logo usage appears correct across light and dark backgrounds. Section dividers, chart slides, and summary slides are consistently styled.

**However, there are 3 critical bugs and 4 major content gaps that must be resolved before this deck is shared with any client or presented in a review.**

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 Critical | 3 | Python format string placeholders not filled (`{overall_rate:.1f}%` etc.) |
| 🟠 Major | 4 | Slides with no body content (empty Executive Summary, empty Summary, 2 missing charts) |
| 🟡 Minor | 3 | N/A value unexplained, title wrapping, potential 3-font-size mix on chart slides |
| ✅ Pass | — | Brand colors, fonts, logo, overall layout consistency, confidentiality footers |

---

## Slide-by-Slide Findings

### Section: Cover & Dashboard (Slides 1–2)

| Slide | Title | Status | Severity | Finding | Fix |
|-------|-------|--------|----------|---------|-----|
| 1 | Cover — First Central CU | ✅ Pass | — | Navy background, white logo, Montserrat ExtraBold title. Compliant. | None |
| 2 | Executive Dashboard | 🟡 Warning | Minor | "N/A" displayed for Reg E Opt-In with no explanation. Reviewers will ask why. | Add a brief note (e.g., "Opt-in data not yet available" or the actual value) either inline or in speaker notes. |

---

### Section: Program Performance (Slides 3–9)

| Slide | Title | Status | Severity | Finding | Fix |
|-------|-------|--------|----------|---------|-----|
| 3 | Section Divider — Program Performance | ✅ Pass | — | Navy section divider, consistent with brand. | None |
| 4 | Executive Summary | 🔴 Fail | Major | Slide contains **only the title** — the body placeholder is completely empty. No summary narrative. | Populate with 3–5 bullet points summarizing key program findings for the period. Move supporting detail to speaker notes. |
| 5 | Monthly Revenue – Last 12 Months | 🔴 Fail | Major | Title-only slide. **The chart image was not embedded.** The slide uses the chart layout (slideLayout9) with a `blipFill` placeholder but no image is referenced — the chart slot is empty. Compare to slide 8 which correctly embeds its chart via `rId2`. | Re-run chart generation for this slide and embed the Monthly Revenue L12M chart image. |
| 6 | ARS Lift Matrix | 🔴 Fail | Major | Same issue as slide 5 — **chart image missing.** Title only, empty chart placeholder. | Re-run chart generation and embed the ARS Lift Matrix chart image. |
| 7 | Section Divider — ARS Mailer Revisit | ✅ Pass | — | Consistent with brand section divider style. | None |
| 8 | Revenue chart (image) | ✅ Pass | — | Chart image embedded correctly. | None |
| 9 | Chart (image) | ✅ Pass | — | Chart image embedded correctly. | None |

---

### Section: Mailer Summaries (Slides 10–13)

| Slide | Title | Status | Severity | Finding | Fix |
|-------|-------|--------|----------|---------|-----|
| 10 | Mailer Summaries | ✅ Pass | — | Section divider, consistent style. | None |
| 11 | All Program Results | ✅ Pass | — | Section title with client/date stamp. | None |
| 12 | All-Time Mailer Summary (Slide 2 of group) | 🔴 Fail | **Critical** | Contains raw Python format strings: **`{overall_rate:.1f}%`**, **`{total_resp:,} respondents across {total_mailed:,} mailed`**. These are unrendered code placeholders — the template substitution failed for this slide. If shown, this exposes internal tooling. | Run the pipeline substitution for ODD group 5 summary stats and replace placeholders with actual values. |
| 13 | Data Check Overview | ✅ Pass | — | Title + subtitle present. Compliant section intro. | None |

---

### Section: Program Analysis (Slides 14–65)

This section contains 52 slides covering DCTR, Reg E, Attrition, and Mailer Campaign performance. All are chart/data slides using images or embedded content.

| Status | Finding |
|--------|---------|
| ✅ Pass | Chart slides (15–16, 18–26, 28–32, 34–43, etc.) all have embedded images correctly referenced. |
| ✅ Pass | Section question dividers (slides 14, 17, 27, 33, 44) use the navy question-format layout consistently. |
| 🟡 Warning (Minor) | **Slide 27 title wraps to 3 lines** ("Are Members Opting In to Overdraft Protection?"). Under the Exception Policy, section divider slides are exempt from the one-line title rule. However, consider shortening to "Are Members Opting In?" with the full text in speaker notes for tighter visual impact. |
| ✅ Pass | Insight callout slides (36, 40, 41, 42, 43) follow the "one takeaway per slide" rule well. Titles are action-oriented and specific. |

**Notable chart slides — no issues:**  
Slides 45–65 (individual mailer KPI layouts) use a consistent multi-panel format with KPI stats, donut chart, response share bars, and demographic callout boxes. Content is dense but appropriate for an internal CSM review deck, and the controlled exception for chart/data slides applies.

---

### Section: Mailer All-Time Summary (Slide 52–53)

| Slide | Title | Status | Severity | Finding | Fix |
|-------|-------|--------|----------|---------|-----|
| 52 | ARS Response – All-Time Mailer Summary | ✅ Pass | — | Chart and content present. | None |
| 53 | All-Time Summary (Slide 2 of group) | 🔴 Fail | **Critical** | Same unfilled placeholders as slide 12: **`{overall_rate:.1f}%`**, **`{total_resp:,} respondents across {total_mailed:,} mailed`**. | Same fix as slide 12 — populate with ODD group 5 all-time summary stats. |

---

### Section: What Should We Do Next / Opportunity (Slides 66–79)

| Status | Finding |
|--------|---------|
| ✅ Pass | Section divider slide 66 ("What Should We Do Next?") is visually strong — navy background, large ExtraBold title. |
| ✅ Pass | Opportunity matrix slides (67–72) use clear chart + callout structure. |
| ✅ Pass | Slides 73–79 (Three Actions, DCTR Progression, Cumulative Value, Branch Scorecards) are internally consistent. |

---

### Section: Summary & Appendix (Slides 80–167)

| Slide | Title | Status | Severity | Finding | Fix |
|-------|-------|--------|----------|---------|-----|
| 80 | Summary & Key Takeaways | 🔴 Fail | Major | **Title only — no takeaway content.** Body placeholder is empty. This is the closing summary slide and needs to contain the actual takeaways. | Populate with 3–5 bullets summarizing key outcomes, performance highlights, and next steps. Move supporting detail to speaker notes. |
| 81 | Appendix — Section Divider | ✅ Pass | — | Clean section break. | None |
| 82–167 | Appendix chart slides | ✅ Pass | — | Historical analysis charts, seasonal analysis, decade views, per-campaign mailer detail. All have embedded chart images. Confidentiality footers present. | None |
| 167 | All-Time Summary Trailer Slide | 🔴 Fail | **Critical** | Same unfilled placeholders: **`{overall_rate:.1f}%`**, **`{total_resp:,} respondents across {total_mailed:,} mailed`**. ODD group 6. | Populate with ODD group 6 all-time summary stats. |

---

## Brand Compliance Checklist

| Rule | Status | Notes |
|------|--------|-------|
| CSI color theme | ✅ Pass | Theme name "2024 CSI Brand Colors". Navy `#00274C`, Orange `#F15D22`, Red `#EB2A2E`, Gold `#F8971D` all correctly defined. |
| Font — Montserrat ExtraBold (headings) | ✅ Pass | Defined in theme `majorFont` and confirmed in slide master. |
| Font — Montserrat (body) | ✅ Pass | Defined in theme `minorFont`. |
| Logo — white on dark | ✅ Pass | Navy/dark section divider slides appear to use white-text CSI logo. |
| Logo — standard on light | ✅ Pass | Light-background slides use standard CSI logo. |
| One message per slide | ✅ Pass | Chart slides each address a single analytical question. |
| Section dividers | ✅ Pass | Consistent navy + large question-format titles throughout. |
| Confidentiality footer | ✅ Pass | "Confidential — for internal CSM/client use only" present on chart slides. |
| No dense paragraphs | ✅ Pass | Insight callout slides use short action-title phrases. |
| Source attribution | ✅ Pass | "First Central CU ODD, [n]" source noted on summary slides. |
| No 3D charts | ✅ Pass | Not observed. |

---

## Fix Priority Queue

Fix these in order before the next review:

**Stop-ship items (cannot share with client or use in presentation):**

1. **Slide 12** — Fill `{overall_rate:.1f}%`, `{total_resp:,}`, `{total_mailed:,}` with ODD group 5 mailer totals.
2. **Slide 53** — Same as above (same ODD group 5, all-time summary context).
3. **Slide 167** — Fill same placeholders with ODD group 6 all-time summary totals.
4. **Slide 5** — Embed the Monthly Revenue L12M chart image.
5. **Slide 6** — Embed the ARS Lift Matrix chart image.

**Should fix before client delivery:**

6. **Slide 4** — Populate Executive Summary body with 3–5 narrative bullets.
7. **Slide 80** — Populate Summary & Key Takeaways with closing bullets.

**Nice to fix:**

8. **Slide 2** — Add note explaining the Reg E Opt-In "N/A" value.
9. **Slide 27** — Consider shortening the section title to fit one line.

---

## Exceptions Documented

| Slide(s) | Exception Type | Reason | Review Needed |
|----------|---------------|--------|--------------|
| 45–65, 106–166 | Chart/data slide — exceeds 3 major points | Mailer KPI layout is intentionally dense for internal CSM review. Single analytical question per slide. | No |
| 27 | Title wraps > 1 line on section divider | Question length required for clarity; section divider exempt from 1-line rule | No |
| 81–167 | Appendix slides — may exceed 3 major points | Clearly marked Appendix; historical reference material | No |

---

## Human Review Items

- None of the CSI logo, co-branding, legal language, or third-party content flags were triggered.
- This deck is marked internal/CSM use only — confirm that designation is correct before any client-facing use.
- Deck is **ready for review** pending the stop-ship fixes above. Do not mark as approved until placeholders are resolved and missing charts are embedded.
