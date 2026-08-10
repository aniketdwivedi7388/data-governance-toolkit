# CDO KPI Framework

**Measuring governance is the hardest and most-faked part of the discipline.**

The reason is structural: the outputs of governance are absences. A regulatory finding that did not happen, a decision that was not made on a wrong number, a migration that did not break. Absences do not show up in a dashboard, so programmes measure the things that do — terms written, rules deployed, policies published — and end up reporting effort as though it were effect.

This framework is built around one rule: **every KPI must be something that could get worse if the function stopped working.** If a metric only ever goes up, it is measuring your activity, not the organisation's condition.

---

## 1. The trap: activity metrics dressed as outcomes

Activity metrics are seductive because they are easy to collect, always improve, and make a good slide. They are also unfalsifiable — no value of "number of glossary terms" tells you whether anyone can trust a number.

| Vanity metric | Why it fails | Measure instead |
|---|---|---|
| Number of glossary terms | Rises with effort, not with clarity. 8,000 auto-loaded terms score higher than 200 curated ones | **Proportion of executive-report metrics with an approved, owned definition** |
| Number of DQ rules deployed | Rewards volume; a team can deploy 500 unowned rules in a sprint | **Proportion of critical data elements passing all error-severity rules** |
| Number of datasets catalogued | Crawlers inflate it overnight | **Proportion of datasets consumed in the last 90 days that have an owner and a description** |
| Policies published | Policy is cheap; control is expensive | **Proportion of policy statements with an operating control producing evidence** |
| Stewards appointed | Names on a slide | **Proportion of stewards who closed at least one item in the last 30 days** |
| Council meetings held | Attendance is not a decision | **Decisions recorded per council session, and median age of open escalations** |
| Training completions | Completion is not comprehension | **Proportion of new datasets onboarded with owner, classification and retention set** |
| Issues raised | Rises when detection improves *and* when quality degrades. Ambiguous by construction | **Median age of open issues, and downstream-patch to upstream-fix ratio** |
| Lineage nodes captured | A crawler can produce millions of meaningless edges | **Proportion of critical reports with column-level lineage to a certified source** |
| Data quality score (composite) | Averages away everything actionable; cannot move for a recognisable reason | **Pass rate by dimension, by consuming obligation** |

**The reframing pattern is always the same:** convert a count into a proportion of something the business cares about, with a defined denominator. The denominator is where the honesty lives. "Terms approved" means nothing; "terms approved out of the terms cited in the regulatory return" means something, and it can go down.

---

## 2. The KPI framework

Seven categories. Twenty-one KPIs. **You will not run all of them** — pick three to five per category at most, and fewer at the start. Each entry gives definition, formula, grain, target guidance, source, and how it gets gamed.

Notation: `|X|` is the count of set X.

### 2.1 Coverage

Is governance reaching the data that matters, rather than the data that was easy?

#### C1. Executive metric definition coverage
- **Definition:** Metrics appearing in the executive reporting pack that have an approved glossary definition with a named owner.
- **Formula:** `|metrics with approved owned definition| / |metrics in the exec pack|`
- **Grain:** Per reporting pack, monthly.
- **Target:** This is one of the few where a high absolute target is defensible — the denominator is small and fully enumerable. Start from your measured baseline and set a quarterly increment you can actually staff.
- **Source:** Glossary export joined to a manually maintained inventory of the reporting pack.
- **Gamed by:** Shrinking the denominator — quietly narrowing what counts as "the exec pack". Fix the pack inventory in the decision register and require council approval to change it.

#### C2. Critical data element ownership
- **Definition:** Critical data elements with a named individual owner who has attested within the review cycle.
- **Formula:** `|CDEs with current attestation| / |CDEs|`
- **Grain:** Per domain, quarterly.
- **Target:** Baseline first. Expect the first measurement to be uncomfortable; that is the point.
- **Source:** Catalogue responsibilities plus attestation dates.
- **Gamed by:** Attesting in bulk without review, and by classifying fewer elements as critical. Sample-audit attestations, and require council sign-off on removals from the CDE list.

#### C3. Domain coverage of the estate
- **Definition:** Datasets in active use assigned to exactly one owning domain.
- **Formula:** `|datasets with exactly one domain| / |datasets queried in last 90 days|`
- **Grain:** Enterprise, quarterly.
- **Target:** Baseline-derived. Note the denominator excludes dormant assets deliberately — governing unused data is waste.
- **Source:** Catalogue domain assignment joined to platform query logs.
- **Gamed by:** Assigning everything to a catch-all "shared" domain. Exclude catch-alls from the numerator explicitly.

### 2.2 Quality

Is the data fit for its declared use, and is that improving?

#### Q1. Critical element quality pass rate
- **Definition:** Critical data elements passing all their error-severity rules over the period.
- **Formula:** `|CDEs with zero unresolved error breaches| / |CDEs with at least one rule|`
- **Grain:** Per domain, per dimension, monthly.
- **Target:** Derived from observation. Never set before you have 4–8 weeks of baseline (see the promotion example in the rule catalogue).
- **Source:** Rule execution results.
- **Gamed by:** Loosening thresholds, downgrading rules from error to warn, or leaving rules at info indefinitely. Publish threshold changes and severity downgrades as a companion metric — a rate that improves alongside a wave of threshold changes tells its own story.

#### Q2. Quarantine ageing
- **Definition:** Median and 90th-percentile age of records held in quarantine.
- **Formula:** `median(now - quarantine_entry_ts)` over open quarantine
- **Grain:** Per domain, weekly.
- **Target:** Set from your triage SLA. Age matters more than depth — depth measures the problem, age measures your response.
- **Source:** Quarantine store.
- **Gamed by:** Bulk-releasing aged records without triage. Track release-without-triage as a separate count.

#### Q3. Upstream fix ratio
- **Definition:** Share of remediations resolved at source rather than patched downstream.
- **Formula:** `|upstream fixes| / (|upstream fixes| + |downstream patches|)`
- **Grain:** Per source system, quarterly.
- **Target:** Direction over level. A ratio flat and low for three quarters means the function is permanently subsidising a source system's defects.
- **Source:** Issue register resolution classification.
- **Gamed by:** Misclassifying patches as fixes. Require the upstream fix to reference a source-system release.

### 2.3 Findability and metadata

Can people find the data, understand it, and tell whether to trust it?

#### M1. Consumed-asset documentation
- **Definition:** Actively consumed datasets with an owner, a business description and a classification.
- **Formula:** `|documented consumed datasets| / |datasets queried in last 90 days|`
- **Grain:** Per domain, monthly.
- **Target:** Baseline-derived, weighted toward the most-queried assets first.
- **Source:** Catalogue joined to query logs.
- **Gamed by:** Auto-generating descriptions from column names. Sample-review descriptions for meaning, and reject any that restate the name.

#### M2. Search-to-answer success
- **Definition:** Catalogue searches that result in the user opening an asset and no repeat search on the same terms within the session.
- **Formula:** `|successful search sessions| / |search sessions|`
- **Grain:** Enterprise, monthly.
- **Target:** Trend, not level. Absolute values depend on tooling and are not comparable to anything.
- **Source:** Catalogue usage telemetry.
- **Gamed by:** Hard to game, easy to misread. Falling success can mean worse metadata *or* a broader user base asking harder questions. Read it alongside adoption.

#### M3. Certified lineage coverage
- **Definition:** Critical reports with unbroken column-level lineage back to a certified source.
- **Formula:** `|critical reports with complete lineage| / |critical reports|`
- **Grain:** Enterprise, quarterly.
- **Target:** Start with the regulatory and executive reports only. A small honest denominator beats a large fictional one.
- **Source:** Lineage graph traversal from report field to certified dataset.
- **Gamed by:** Counting manually declared lineage as equivalent to harvested. Report harvested and declared separately.

### 2.4 Issue management

When something is wrong, how quickly and how permanently is it fixed?

#### I1. Median time to triage
- **Definition:** Elapsed time from breach detection to a triage decision.
- **Formula:** `median(triage_ts - detection_ts)`
- **Grain:** Per domain, weekly.
- **Target:** From your published SLA. This is a capacity metric — when it rises, you are out of steward capacity, not out of process.
- **Source:** Issue register.
- **Gamed by:** Triaging quickly and superficially. Pair with the reopen rate.

#### I2. Issue reopen rate
- **Definition:** Closed issues reopened within 90 days.
- **Formula:** `|reopened within 90d| / |closed in period|`
- **Grain:** Per domain, quarterly.
- **Target:** Low and stable. A rising rate means issues are being closed rather than resolved.
- **Source:** Issue register state history.
- **Gamed by:** Raising a new issue instead of reopening. Detect by clustering on the same asset and rule.

#### I3. Consumer-detected defect share
- **Definition:** Confirmed incidents first reported by a consumer rather than by a control.
- **Formula:** `|consumer-detected incidents| / |confirmed incidents|`
- **Grain:** Enterprise, quarterly.
- **Target:** Falling. This is the best single proxy for whether controls are pointed at the right places.
- **Source:** Issue register detection-source field.
- **Gamed by:** Recording the control as the source when a consumer prompted the check. Capture detection source at raise time, before investigation starts.

### 2.5 Access and compliance

Do the right people have the right access, and can you prove it?

#### A1. Entitlement recertification effectiveness
- **Definition:** Entitlements revoked as a result of a recertification campaign.
- **Formula:** `|revoked during campaign| / |reviewed|`
- **Grain:** Per campaign, per domain.
- **Target:** **Not zero.** A campaign that revokes nothing is a rubber stamp. Report alongside completion rate, and treat a near-100% re-attestation rate as a finding rather than a success.
- **Source:** Identity and access management logs.
- **Gamed by:** Bulk approval. Sample-audit approvals and time-box the review UI.

#### A2. Restricted data access provenance
- **Definition:** Active entitlements to restricted-classification data with a recorded approver and business justification.
- **Formula:** `|entitlements with approver and justification| / |active restricted entitlements|`
- **Grain:** Enterprise, quarterly.
- **Target:** This is an audit-facing control; the defensible target is complete coverage, and gaps should be treated as exceptions with dates.
- **Source:** IAM joined to catalogue classification.
- **Gamed by:** Boilerplate justifications. Review a sample for specificity.

#### A3. Onboarding gate compliance
- **Definition:** New data sources reaching production with owner, classification and retention rule set before go-live.
- **Formula:** `|compliant onboardings| / |sources onboarded in period|`
- **Grain:** Enterprise, quarterly.
- **Target:** Complete, because the cost of compliance at onboarding is near zero and the cost of retrofit is high.
- **Source:** Onboarding workflow records joined to catalogue.
- **Gamed by:** Onboarding outside the process. Reconcile against platform-created datasets, not against the workflow's own record of itself.

### 2.6 Adoption

Is anyone using this, or are you building for an audience of one?

#### D1. Active glossary consumption
- **Definition:** Distinct users viewing or referencing glossary terms in the period.
- **Formula:** `distinct_users(glossary_views)` and `/ |eligible users|` for rate
- **Grain:** Enterprise, monthly.
- **Target:** Trend. Segment by business versus technical users — a glossary read only by engineers has not landed.
- **Source:** Catalogue telemetry.
- **Gamed by:** Mandated training clicks. Exclude sessions originating from training links.

#### D2. Certified-source usage share
- **Definition:** Query volume against certified datasets versus equivalent uncertified copies.
- **Formula:** `queries(certified) / (queries(certified) + queries(known duplicates))`
- **Grain:** Per domain, quarterly.
- **Target:** Rising. This is one of the strongest adoption signals available because it measures behaviour, not opinion.
- **Source:** Platform query logs plus a maintained duplicate register.
- **Gamed by:** An incomplete duplicate register flatters the numerator. Refresh the register from lineage, not from memory.

#### D3. Steward engagement
- **Definition:** Appointed stewards who closed at least one item in the last 30 days.
- **Formula:** `|active stewards| / |appointed stewards|`
- **Grain:** Per domain, monthly.
- **Target:** High. A persistently inactive steward is either unnecessary or unsupported — both need action.
- **Source:** Workflow and issue register assignment history.
- **Gamed by:** Trivial closures. Spot-check what was closed.

### 2.7 Value realisation

The category everyone wants and nobody can evidence cleanly. §5 covers what you can defend.

#### V1. Reconciliation effort avoided
- **Definition:** Analyst hours previously spent reconciling conflicting figures, removed by a single certified source.
- **Formula:** `hours_before - hours_after`, measured on a named process
- **Grain:** Per named process, per initiative.
- **Target:** Not a target — an evidenced claim, measured once with the process owner's sign-off.
- **Source:** Time study or process owner attestation, before and after.
- **Gamed by:** Extrapolating one process across the enterprise. Never extrapolate. Report the processes you measured.

#### V2. Change lead time for data-affecting changes
- **Definition:** Elapsed time from proposed schema or definition change to approved implementation.
- **Formula:** `median(approved_ts - proposed_ts)`
- **Grain:** Per domain, quarterly.
- **Target:** Falling. Governance is usually accused of slowing change; this is where you either disprove it or find out it is true.
- **Source:** Change workflow records.
- **Gamed by:** Excluding changes that stalled before formal proposal. Measure from first raise, not from formal submission.

#### V3. Audit and regulatory finding recurrence
- **Definition:** Data-related audit findings that recur after being closed.
- **Formula:** `|recurring findings| / |closed findings|`
- **Grain:** Enterprise, annually.
- **Target:** Zero recurrence is the defensible ambition. Recurrence is the clearest evidence that a remediation was cosmetic.
- **Source:** Audit tracking system.
- **Gamed by:** Rewording a finding so it counts as new. Have the audit function classify recurrence, not the governance function.

---

## 3. Leading versus lagging indicators

Lagging indicators tell you what happened. Leading indicators tell you what is about to. A scorecard of only lagging indicators means every conversation is retrospective.

| Leading (predicts) | Lagging (confirms) | The link |
|---|---|---|
| Quarantine ageing rising | Consumer-detected defects rise next quarter | Untriaged data reaches consumers |
| Steward engagement falling | Time to triage rises | Capacity leaves before throughput drops |
| Threshold-loosening events | Quality pass rate improves artificially | The metric improves while the data does not |
| Onboarding gate compliance falling | Ownership and classification coverage fall | Ungoverned assets accumulate silently |
| Open escalation age rising | Council decisions per session fall | Decisions are stalling before they are visible |
| Lineage gap count rising | Impact analysis misses a consumer | Coverage decays before it fails |
| Certified-source usage share flat | Reconciliation disputes persist | Adoption has stalled regardless of build progress |

**Put two or three leading indicators on the executive scorecard.** They are what make the conversation about next quarter rather than last.

---

## 4. Executive scorecard

One page. If it needs a second page, it is a working-group pack, not an executive scorecard.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  DATA GOVERNANCE SCORECARD                          Period: 2026 Q2         │
│  Prepared by Data Governance Office            Baseline set: 2025 Q3        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TRUST IN THE NUMBERS                    Now    Prev   Base   Dir   Status  │
│    Exec metrics with owned definition    78%    71%    34%     ▲     amber  │
│    Critical elements passing all rules   91%    89%    76%     ▲     green  │
│    Defects found by consumers first      22%    31%    64%     ▼     amber  │
│                                                                             │
│  RESPONSIVENESS                          Now    Prev   Base   Dir   Status  │
│    Median time to triage (hours)         14     11     72      ▲     amber  │
│    Quarantine age P90 (days)             9      6      -       ▲     red    │
│    Issues reopened within 90 days        7%     9%     18%     ▼     green  │
│                                                                             │
│  CONTROL AND COMPLIANCE                  Now    Prev   Base   Dir   Status  │
│    Onboarding gate compliance            94%    88%    41%     ▲     green  │
│    Recertification revocation rate       6%     8%     -       ▼     green  │
│    Recurring audit findings              0      1      3       ▼     green  │
│                                                                             │
│  ADOPTION                                Now    Prev   Base   Dir   Status  │
│    Certified-source usage share          64%    58%    29%     ▲     amber  │
│    Active stewards                       82%    85%    -       ▼     amber  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  WATCH — leading indicators moving the wrong way                            │
│    Quarantine P90 up 50% and steward engagement down 3pt. Both point at     │
│    triage capacity in two domains. Expect time-to-triage to worsen next     │
│    quarter unless capacity is added.                                        │
│                                                                             │
│  DECISIONS REQUESTED                                                        │
│    1. Approve 0.5 FTE additional stewardship in the two affected domains    │
│    2. Confirm Q3 scope: extend coverage to the regulatory return pack       │
│                                                                             │
│  NOT MEASURED — stated deliberately                                         │
│    Financial benefit of improved quality. See value-attribution note.       │
└─────────────────────────────────────────────────────────────────────────────┘
```

Four design choices worth copying:

- **Baseline column, always.** Progress from a measured starting point is credible; a number against a round target is not.
- **Direction arrows, not just values.** Direction is what the conversation is about.
- **A decisions-requested block.** A scorecard with no ask is a status update, and status updates get skimmed.
- **A "not measured" line.** Stating what you deliberately do not claim buys more credibility than any number on the page.

### Reporting cadence

| Audience | Cadence | Content | Length |
|---|---|---|---|
| Working group | Weekly | Operational queues: breaches, quarantine age, open issues, terms awaiting decision | Dashboard, no deck |
| Domain lead | Monthly | Domain scorecard with per-steward throughput | 1 page |
| Council | Monthly | Enterprise scorecard, escalations, decisions requested | 1 page + papers |
| Executive sponsor | Quarterly | The one-pager above, with the watch list and asks | 1 page |
| Audit and risk | Semi-annual or on demand | Control evidence, findings status, exception register | Evidence pack |

**Do not report the same numbers at all levels.** An executive does not need quarantine depth by rule; a steward cannot act on an enterprise pass rate. Mismatched grain is the most common reason scorecards get ignored.

---

## 5. Attributing business value — honestly

This is where credibility is won or lost. The temptation is to claim a large financial benefit; the risk is that finance tests one number, finds it unsupportable, and discounts everything else you have said for two years.

### What you can defend

| Claim | Why it holds | How to evidence |
|---|---|---|
| Effort removed from a named process | Directly observable, bounded | Time study before and after, signed by the process owner |
| Reduction in a specific regulatory finding | The finding exists in writing | Audit tracking record |
| Faster change delivery for data-affecting changes | Measured in your own workflow | Change lead time, before and after |
| A specific incident prevented by a control that fired | Traceable to a rule execution | Rule result, quarantine record, impact assessment |
| Decommissioning cost avoided | Lineage proved no consumers remained | Lineage evidence plus the retained platform cost |
| Licence or storage cost removed | Duplicate datasets retired | Platform billing, before and after |

### What you cannot defend

| Claim | Why it fails |
|---|---|
| "Governance delivered £Xm in benefit" | No counterfactual. Nobody ran the organisation without it in parallel |
| "Improved data quality increased revenue by X%" | Uncontrolled confounders. Markets, pricing, staffing and product all moved too |
| "We avoided a fine of £Xm" | The fine did not happen. You cannot price an absence you never observed |
| "Better decisions were made" | Unmeasurable without a decision-quality baseline nobody has |
| Industry benchmark extrapolation | A published average applied to your organisation is not evidence about your organisation |

### How to talk about the undefendable

Do not claim it — **frame it as risk reduction, and be explicit that it is not a financial benefit**:

> "We cannot attribute revenue to governance and we will not try. What we can show is that consumer-detected defects fell from 64% to 22% of confirmed incidents, that no data-related audit finding recurred this year, and that the two most-disputed executive metrics now have single owned definitions. Those are the conditions under which decisions are made on correct numbers. Pricing that is a judgement for this forum, not a calculation we can produce."

That paragraph survives scrutiny. A benefit figure with a footnote does not.

### The one number worth computing

**Cost of the function versus cost of the alternative.** Governance cost is knowable — headcount plus tooling. The alternative is partly knowable: reconciliation effort in named processes, remediation effort on incidents, audit remediation cost. It will not produce a flattering ratio in year one and should not be presented as though it will. Presenting it honestly, with the parts you cannot quantify listed as unquantified, is more persuasive than a business case that claims certainty.

---

## 6. Metrics that get gamed

Every metric with a consequence attached will be gamed. This is not cynicism — it is the predictable response to a target, and the mitigation is designed in, not exhorted away.

| Metric | Gaming behaviour | Mitigation |
|---|---|---|
| Quality pass rate | Thresholds loosened; rules downgraded to warn; rules quietly disabled | Publish threshold-change and severity-downgrade events as a companion metric. A pass rate rising alongside a wave of changes explains itself |
| Coverage percentages | Denominator narrowed — fewer elements classified critical, fewer reports called critical | Fix denominators in the decision register; changes require council approval and are shown on the scorecard |
| Time to triage | Superficial triage to stop the clock | Pair with reopen rate and false-positive rate |
| Issue count | Stop raising issues; handle them informally | Track consumer-detected share, which rises when issues go unrecorded |
| Recertification completion | Approve everything without reading | Publish revocation rate; treat near-100% re-attestation as a finding |
| Glossary term count | Bulk-load column names as terms | Do not report the count at all. Report coverage of a fixed denominator |
| Lineage coverage | Manual declarations counted as harvested | Report harvested and declared separately and never merge them |
| Steward engagement | Trivial closures to register activity | Spot-check closures; measure items closed with a recorded root cause |
| Adoption | Mandated clicks | Exclude training-originated sessions; prefer behavioural metrics like certified-source usage share |
| Composite quality score | Weightings adjusted until the number improves | Do not build one. If forced, freeze weightings for a year and publish them |

### Three design rules that reduce gaming

1. **Fix the denominator publicly.** Most gaming is denominator manipulation, and it is nearly invisible unless the denominator is a governed artefact in its own right.
2. **Pair every efficiency metric with a quality metric.** Speed alone is always gameable; speed plus rework rate is not.
3. **Never attach individual performance objectives to a metric you have not tested for a year.** The fastest route to a corrupted metric is making someone's rating depend on it before you understand its failure modes.

---

## Related

- [`../glossary/business-glossary-template.md`](../glossary/business-glossary-template.md) — the coverage denominator starts with the executive metric inventory
- [`../quality/dq-rule-catalogue.md`](../quality/dq-rule-catalogue.md) — threshold derivation behind the quality KPIs
- [`../stewardship/operating-model.md`](../stewardship/operating-model.md) — the maturity ladder these KPIs evidence
- [`../lineage/lineage-capture-guide.md`](../lineage/lineage-capture-guide.md) — lineage coverage measurement
