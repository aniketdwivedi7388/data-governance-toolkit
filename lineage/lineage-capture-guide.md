# Lineage Capture Guide

**Nobody wants lineage. They want to answer a question, and lineage is what makes the answer cheap.**

That distinction decides everything else in this document. Lineage built as a documentation exercise produces a large graph nobody queries. Lineage built backwards from four specific questions produces something people open under pressure.

The four questions:

| Question | When it is asked | Required granularity |
|---|---|---|
| **What breaks if I change this?** | Before a schema or definition change | Column-level, downstream, including BI fields |
| **Why is this number wrong?** | During an incident, usually with an audience | Column-level plus transformation logic, upstream |
| **Where did this regulatory figure come from?** | Under examination | Column-level, upstream, with evidence and as-of dates |
| **Can I safely switch this off?** | Decommissioning | Dataset-level downstream, complete rather than deep |

**The use case determines the granularity, and therefore the cost.** Decommissioning needs breadth, not depth: a complete dataset-level graph is enough. Root-cause analysis needs depth: without transformation logic you know a column contributed but not how. Building column-level lineage across an entire estate because "we need lineage" is how programmes spend two years and deliver a graph that answers none of these well.

---

## 1. Granularity levels

| Level | What it records | Answers | Effort | Decay rate | Worth it when |
|---|---|---|---|---|---|
| **System** | Platform A feeds platform B | Rough blast radius; architecture conversations | Days | Slow | Always — it is nearly free and orients everyone |
| **Dataset** | Table X derives from tables Y and Z | Decommissioning; ownership routing; coarse impact | Weeks | Medium | The default baseline for the whole estate |
| **Column** | Column `a.x` derives from `b.y` and `c.z` | Impact analysis; root cause; regulatory traceability | Months | Fast | Critical reporting paths and regulated data only |
| **Transformation logic** | The expression producing the column | Why the value is what it is; reproducing a figure | Months, ongoing | Fastest | Regulatory figures and disputed metrics |
| **Row / value provenance** | Which input rows produced this output row | Auditing an individual record | Very high, storage-heavy | N/A | Rarely. Specific regulatory or model-explanation needs |

### The pragmatic shape

**Dataset-level everywhere, column-level on the paths that matter, transformation logic on the figures you have to defend.** Attempting column-level everywhere produces a graph that is 60% complete and 100% untrusted — and a lineage graph people do not trust is worse than none, because it produces confident wrong answers during impact analysis.

Row-level provenance deserves a warning: it is a fundamentally different engineering problem with storage costs proportional to data volume. Do not let it into scope because someone said "full lineage".

---

## 2. Capture approaches

| Approach | How it works | Accuracy | Cost to build | Coverage | Staleness | Fits |
|---|---|---|---|---|---|---|
| **Platform metadata harvesting** | Read the engine's own metadata and query history | High within the platform; blind outside it | Low — often configuration | Whatever runs on that platform | Low: refreshes on schedule | Your primary warehouse or lakehouse |
| **Static SQL and code parsing** | Parse DDL, DML, notebooks, transformation code | High for standard SQL; degrades on dynamic constructs | Medium | Anything with readable code | Medium: reflects code, not execution | Version-controlled transformation layers |
| **Runtime and observability capture** | Emit lineage events as jobs execute | Highest — records what actually ran | Medium to high; needs instrumentation | Instrumented jobs only | Lowest: current by construction | Orchestrated pipelines you control |
| **Manual declaration** | Humans record the hop | Accurate at capture, decays immediately | Low per hop, unbounded in aggregate | Anything, including spreadsheets | Highest | Last resort, for hops nothing else reaches |
| **Log and access-based inference** | Infer from query and access logs | Suggestive, not authoritative | Low | Broad | Low | Discovery and gap-finding, not evidence |

### How to combine them

Almost every real deployment is a hybrid, and the value is in the seams:

1. **Harvest from the platform first.** It is the cheapest coverage you will ever get, and it establishes the backbone.
2. **Parse the transformation layer** to add column-level detail the platform metadata does not expose.
3. **Instrument runtime for the critical paths** where you must know what actually executed, not what the code says.
4. **Manually declare only what nothing else reaches** — and put an expiry date on every manual edge.
5. **Use access logs to find the gaps**, not to fill them. A dataset with heavy read traffic and no downstream lineage is a hole in your graph, and that is the highest-value thing log inference tells you.

### Mark provenance on every edge

Every edge should carry how it was captured. Without it, a manually declared edge from eighteen months ago looks identical to a runtime-captured edge from last night, and a reviewer cannot tell which to trust.

```yaml
edge:
  source: warehouse.client_master.client_id
  target: mart.client_summary.client_id
  capture_method: runtime          # harvested | parsed | runtime | declared | inferred
  captured_at: "2026-08-09T02:14:00Z"
  captured_by: pipeline_run_88421
  confidence: high                 # high | medium | low
  expires_at: null                 # mandatory for declared edges
  transformation: "direct copy"
```

---

## 3. The hard parts

Automated harvesting handles the easy 70%. These four are where the graph breaks, and they are exactly where the questions get asked.

### Through BI tools

The last hop — dataset to report field — is the one business users care about most and the one most often missing. Difficulties compound: semantic layers and calculated fields create derivations invisible to the database; custom SQL embedded in a data source is opaque to the platform; extracts break the live connection entirely; field-level usage is inside proprietary metadata.

What works:

- **Use the BI tool's own metadata API** where one exists. Coverage varies by product and by release — verify against your version rather than trusting a feature matrix.
- **Ban embedded custom SQL for certified reports.** Require a governed view instead. This single policy recovers more BI lineage than any tooling investment.
- **Treat calculated fields as metric definitions** and govern them. A calculated field is a metric hiding in the presentation layer.
- **Register extracts as datasets in their own right.** An extract is a copy with its own freshness and its own lineage, and pretending otherwise hides real staleness.

### Through spreadsheets and manual hops

Someone exports to a spreadsheet, applies judgement, and re-uploads. The lineage graph shows a source and a sink with a hole between them. This is not a tooling failure — it is genuinely uncapturable by automation, because the transformation happened in a human's head.

- **Do not pretend to capture it.** Represent the manual hop as an explicit node of type `manual_process` with a named owner. A visible gap is honest; an invisible gap is a lie the graph tells during impact analysis.
- **Make the node uncomfortable.** Manual hops on a critical path should appear on the risk register. Visibility is the point.
- **Count them as a metric.** Manual hops on critical paths is a leading indicator of where the next incident comes from.
- **Where volume justifies it**, replace the spreadsheet with a governed input application that writes a real table. Then the hop becomes capturable.

### Through stored procedures and dynamic SQL

Static parsing handles a stored procedure with straightforward SQL. It fails on string-concatenated SQL, conditional branches producing different column sets, cursor loops, and table names assembled at runtime.

- **Runtime capture is the only reliable answer.** Capture what executed; do not try to reason about what might.
- **Where runtime capture is unavailable**, parse for the *union* of possible outputs and mark confidence as low. Over-reporting is safer than under-reporting for impact analysis — a false positive costs a check, a false negative costs an outage.
- **Treat unparseable procedures on critical paths as technical debt with a governance consequence**, not just an engineering preference.

### Across organisational boundaries

Lineage stops at the edge of what you operate. Vendor feeds, outsourced processing, data shared with third parties, regulated data leaving the firm.

- **Model the boundary as a node**, typed as external, with the provider named and a contact.
- **Push provenance requirements into contracts.** What the provider must tell you about how a field is derived, and how they notify change. This is far more effective than any technical measure, and it is usually nobody's job to ask for it.
- **For outbound data, lineage becomes a retention and privacy control.** If you cannot enumerate where data went, you cannot evidence deletion.
- **Accept declared lineage at the boundary** and mark it as such, with an expiry.

---

## 4. Why lineage decays, and how to stop it

Lineage is not a document that goes stale slowly. It is a claim about a system that changes weekly, so it decays at the rate of change of your platform.

| Decay cause | What happens | Counter |
|---|---|---|
| Pipeline changed, lineage not updated | Graph describes last quarter's system | Emit lineage from the pipeline at runtime — no separate update step exists to forget |
| New pipeline built outside the standard | Invisible to harvesting | Make lineage emission a deployment gate |
| Harvesting connector breaks silently | Coverage falls; nobody notices because the graph still renders | Alert on *absence* — a source that stopped emitting is an incident |
| Manual declarations never revisited | Confident, wrong edges | Mandatory expiry on declared edges; expired edges render as gaps |
| Assets decommissioned but left in the graph | Impact analysis flags dead consumers; people stop trusting results | Reconcile the graph against the platform inventory monthly |
| Schema evolution | Column renamed; edge orphaned | Handle rename events explicitly in the ingestion path |

### The principle

**Lineage must be a by-product of running the pipeline, not a task performed about the pipeline.**

Any model where a human updates lineage after changing code fails. Not because engineers are careless, but because the update is unrewarded, invisible when skipped, and competes with delivery pressure. It will be skipped, and the graph will be quietly wrong at the exact moment someone relies on it.

Practical implementation:

- Emit lineage events from the orchestrator or transformation framework as part of execution.
- Fail the deployment if a new job produces no lineage event on first run.
- Treat a lineage gap on a critical path as an issue with an owner and an SLA, not a backlog item.
- **Report coverage as a trend, and alert on decline.** Coverage falling is a leading indicator; by the time someone notices the graph is wrong, they noticed during an incident.

---

## 5. Worked example: impact analysis for a column type change

**The proposal.** Widen `client_master.client_ref` from `VARCHAR(12)` to `VARCHAR(20)` to accommodate identifiers from a newly onboarded source.

Sounds trivial. Here is what the analysis actually surfaces.

### Step 1 — direct consumers, one hop

Query the graph for edges where `client_master.client_ref` is the source.

```text
client_master.client_ref
 ├── stg_client.client_ref                    parsed      direct copy
 ├── dim_client.client_ref                    parsed      direct copy
 ├── fact_position.client_ref                 parsed      join key
 └── extract_regulatory_client.client_ref     runtime     direct copy
```

Four direct consumers. If you stop here you will break something — this is the depth at which most impact analyses are performed, and it is why change failures keep happening.

### Step 2 — transitive closure, all downstream

```text
dim_client.client_ref
 ├── mart_client_summary.client_ref           parsed      direct copy
 │    └── BI: Client Overview / Client Ref    harvested   dimension field
 ├── mart_client_summary.client_key           parsed      CONCAT(client_ref,'-',region_cd)   ← ATTENTION
 └── ml_feature_client.client_hash            runtime     SHA256(client_ref)                 ← ATTENTION

fact_position.client_ref
 └── mart_position_daily.client_ref           parsed      join key
      ├── BI: Position Dashboard              harvested   filter and drill field
      └── extract_custodian_recon.client_ref  runtime     fixed-width position 15-26         ← ATTENTION

extract_regulatory_client.client_ref
 └── EXTERNAL: regulatory submission          declared    field 4, max length 12             ← ATTENTION
```

### Step 3 — read the transformations, not just the edges

The edges alone say "twelve things consume this column". The transformation logic says which ones actually break, and they are not the obvious ones:

| Consumer | Transformation | Impact | Severity |
|---|---|---|---|
| `mart_client_summary.client_key` | `CONCAT(client_ref,'-',region_cd)` | Composite key column may overflow its own declared width; key format changes for new records | **High** |
| `ml_feature_client.client_hash` | `SHA256(client_ref)` | Hash is length-agnostic, but any model trained on prefix-derived features sees distribution shift | **Medium** |
| `extract_custodian_recon` | Fixed-width, positions 15–26 | **Silent truncation or field misalignment.** The file will parse and be wrong | **Critical** |
| External regulatory submission | Max length 12, declared edge | Values over 12 characters rejected or truncated by the recipient | **Critical** |
| BI: Client Overview | Dimension field | Column width may need adjusting; cosmetic | Low |
| BI: Position Dashboard | Filter and drill | Saved filters on exact values still work; cosmetic | Low |

**The two critical impacts are both at boundaries the database cannot see** — a fixed-width file format and an external submission specification. Neither would have been found by asking "which tables use this column", which is what a dataset-level graph answers.

### Step 4 — the human layer

The graph gives you assets. Impact analysis needs people. Resolve each affected node to its owner:

- [ ] Owners of all 12 downstream assets identified and notified
- [ ] Fixed-width extract: consuming party contacted, spec change agreed, test file exchanged
- [ ] Regulatory submission: recipient's field specification confirmed; a widening may require prior notification
- [ ] ML feature: model owner confirms retraining is or is not required
- [ ] Composite key: does the change restate existing keys, or apply only to new records
- [ ] Rollback plan agreed with each critical consumer

### Step 5 — the gap check

**Before approving, ask what the graph does not cover.** Query for assets reading `client_master` with no recorded downstream edges. Two appear: a reporting sandbox schema and a scheduled export to a shared drive. Neither is instrumented. Both are manual hops.

**This is the most valuable step and the one most often skipped.** The known unknowns are where change failures live. Two options: instrument them before proceeding, or accept the risk explicitly and record the acceptance. Either is defensible. Not asking is not.

### Outcome

The change proceeds with a coordinated release: the fixed-width extract spec is versioned and the consumer migrated first, the regulatory recipient confirms the wider field, the composite key is applied to new records only with the change effective-dated, and the two ungoverned consumers are instrumented as a condition of approval.

**Elapsed time: about two days.** Without lineage, this is a two-week discovery exercise that still misses the fixed-width extract — which then fails silently in production, produces a reconciliation break three weeks later, and costs more to diagnose than the whole lineage capability cost to build.

---

## 6. Lineage for AI and agentic pipelines

When a model or agent produces an answer, the governance question shifts from "where did this column come from" to **"what grounded this answer, and was that thing fit to ground it?"**

### What to capture

| Element | Why it matters | Capture point |
|---|---|---|
| Retrieved chunks or records, with identifiers | You cannot audit an answer without knowing its inputs | Retrieval layer, per request |
| Source asset for each retrieved item | Links the answer to a governed dataset with an owner and a quality state | Index build time, carried through |
| As-of timestamp of the grounding data | An answer correct last month may be wrong now | Retrieval, from source metadata |
| Quality and certification state at retrieval time | Whether the grounding data was fit at the moment it was used | Retrieval, from catalogue |
| Entitlement context of the caller | Proves the caller was permitted to see what grounded the answer | Pre-retrieval, from identity |
| Prompt and model version | Reproducibility | Runtime |
| Which retrieved items the answer actually cited | Retrieved is not the same as used | Response parsing |

### The pattern

**Treat the vector index and any derived embedding store as datasets with lineage of their own.** They are derived assets: they have a source, a build job, a refresh cadence and a staleness profile. Teams routinely govern the source table and forget that the index built from it three weeks ago is what the agent actually reads. Index staleness is invisible to every control pointed at the source.

Two further points that matter more than they first appear:

- **Retrieved is not the same as used.** If your audit trail records only what was retrieved, you cannot answer "did the answer come from the certified source or the stale one" when both were in context. Capture the citation set, not just the candidate set.
- **Grounding lineage must reach back to business meaning.** "This came from `mart_client_summary`" is weak. "This came from the certified Active Client figure, as defined in the glossary, owned by Client Operations, as at 31 July" is auditable. The join from retrieval provenance back to the glossary term is what makes agent answers defensible.

### Minimum for an agent answering on governed data

```yaml
answer_provenance:
  request_id: req_9f2c41
  answered_at: "2026-08-09T14:22:11Z"
  caller_entitlements_evaluated: true
  grounding:
    - asset: mart.client_summary
      asset_owner: Client Operations
      glossary_terms: [Active Client, Client Segment]
      certification_state: certified
      data_as_of: "2026-07-31"
      index_built_at: "2026-08-08T02:00:00Z"
      retrieved_ids: [cs_00412, cs_00418]
      cited_ids: [cs_00412]
  model_version: <model-id>
  prompt_version: v14
  unresolved_gaps: []
```

If `index_built_at` is materially older than `data_as_of`, the agent answered from stale grounding regardless of how fresh the source table was. **That single comparison catches a failure mode most AI governance frameworks do not mention.**

---

## 7. Minimum viable lineage

For a team starting out. Resist every request to expand this before it is finished and in use.

### Scope

- [ ] **System-level map of the whole estate.** A diagram is acceptable. Days of effort, immediate orientation value.
- [ ] **Dataset-level lineage for your primary analytics platform**, from harvesting. Configuration, not a project.
- [ ] **Column-level lineage for one critical path**, end to end — pick the executive report or regulatory return with the most scrutiny.
- [ ] **The last hop into BI for that one path**, even if declared manually.
- [ ] **Every manual hop on that path modelled as an explicit node** with an owner.
- [ ] **Owner resolution**: every node maps to a person, or the graph cannot support impact analysis.

### Sequence

| Phase | Weeks | Deliverable | Done when |
|---|---|---|---|
| 1 | 1–2 | System map; harvesting connected to the primary platform | Dataset-level graph renders for the main platform |
| 2 | 3–5 | One critical path traced column-level, including BI and manual hops | An engineer can answer "what feeds this figure" without asking anyone |
| 3 | 6–8 | Owner resolution on that path; gaps registered as issues | Every node has a named owner |
| 4 | 9–12 | Use it once, for real, on a live change | An impact analysis was performed from the graph and found something a manual review missed |

**Phase 4 is the only one that matters.** Lineage that has never been used in anger is a project deliverable, not a capability. Until someone has made a decision from it and been right, you do not know whether it works.

### What to defer

Column-level everywhere. Row-level provenance. Historical lineage reconstruction. Lineage for datasets nobody queries. Lineage for systems being decommissioned within the year. All of these are legitimate eventually; none of them belongs in the first quarter.

---

## 8. Tooling evaluation checklist

Product capabilities change release to release. **Verify each of these against the specific version you would deploy, with your own data** — feature matrices describe intent and demos describe the happy path.

### Capture

- [ ] Which of your platforms are supported natively, and at what granularity per platform
- [ ] Column-level or dataset-level only, per connector — this varies within a single product
- [ ] Does it capture transformation logic, or only the edge
- [ ] Static parsing, runtime capture, or both
- [ ] Behaviour on dynamic SQL, stored procedures, and string-built queries
- [ ] Open lineage standards support, for interoperability and exit
- [ ] API for pushing lineage the connectors cannot reach
- [ ] Handling of schema evolution and column renames

### Coverage of the hard parts

- [ ] BI tool support, per tool and per version, including calculated fields and embedded SQL
- [ ] Can a manual or external hop be modelled as a first-class node
- [ ] Cross-platform stitching where a pipeline spans systems
- [ ] File-based and fixed-width interfaces
- [ ] Streaming pipelines
- [ ] Notebook and ad-hoc code
- [ ] Vector indexes and derived AI assets

### Trust and freshness

- [ ] Is capture method visible per edge
- [ ] Confidence indication, and how it is derived
- [ ] Expiry or review on manually declared edges
- [ ] Refresh cadence per connector, and cost of increasing it
- [ ] Alerting when a connector stops producing lineage
- [ ] Reconciliation against platform inventory to find orphans

### Usability

- [ ] Can a business user trace a report field to a source without help
- [ ] Impact analysis in the tool, or export to something that can do it
- [ ] Graph query API — can you ask "all downstream of X within N hops" programmatically
- [ ] Does the graph render usefully at your scale, or become a hairball
- [ ] Integration with the catalogue: does an owner, a term and a quality state appear on a lineage node
- [ ] Export of an impact analysis as evidence for a change record

### Operational

- [ ] Cost model — per asset, per connector, per user, or per volume
- [ ] Effort to add an unsupported source
- [ ] Metadata retention: can you show lineage as it stood on a past date
- [ ] Access control on the lineage graph itself — it reveals structure and can be sensitive
- [ ] Exit: can you extract the full graph in an open format

### The proof-of-concept test

Do not evaluate on a vendor dataset. Take **one real critical path**, ideally an ugly one with a stored procedure, a BI layer and a file interface. Ask the vendor to trace it end to end with your data.

Then ask the question that separates products: **"show me what you could not capture."** A vendor who answers precisely is telling you the truth about the seams, and the seams are where your work will be. A vendor who says everything is covered has either not looked or is not going to tell you.

---

## Related

- [`../quality/dq-rule-catalogue.md`](../quality/dq-rule-catalogue.md) — root-cause analysis depends on lineage
- [`../glossary/business-glossary-template.md`](../glossary/business-glossary-template.md) — impact analysis on a definition change needs term-to-column mappings
- [`../stewardship/raci-template.md`](../stewardship/raci-template.md) — metadata and lineage maintenance RACI
- [`../metrics/cdo-kpi-framework.md`](../metrics/cdo-kpi-framework.md) — lineage coverage as a KPI, and how it gets gamed
