# Data Governance Toolkit

**The working artefacts of a data governance function — templates, rubrics, rule
catalogues and operating models you can pick up and use on Monday.**

Most published material on data governance is either vendor marketing or a
framework diagram with four boxes and an arrow. This repository is the other
thing: the documents a governance team actually produces, in a form you can
copy, adapt and run — plus a small rule engine so the quality half is
executable rather than aspirational.

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![DAMA-DMBOK](https://img.shields.io/badge/aligned-DAMA--DMBOK-1B3A57)](https://www.dama.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## What's here

| Area | Artefact | What you get |
|---|---|---|
| **Glossary** | [business-glossary-template.md](glossary/business-glossary-template.md) | The anatomy of a definition that survives review, approval workflow, anti-patterns, and how to seed a glossary without boiling the ocean |
| | [example-glossary.yaml](glossary/example-glossary.yaml) | Fully worked terms — including a deprecated term pointing at its replacement, and terms with conflicting physical mappings across systems |
| **Quality** | [dq-rule-catalogue.md](quality/dq-rule-catalogue.md) | 60+ reusable rules across the six DQ dimensions, threshold-setting, severity, and the remediation loop |
| | [dq_engine.py](quality/dq_engine.py) | **Runnable.** A YAML-driven rule engine with severity, quarantine and a CI-ready gate |
| **Stewardship** | [operating-model.md](stewardship/operating-model.md) | Roles and what they actually do, forum structure with decision rights, domain design, a 90-day stand-up plan, and a maturity ladder with observable behaviours |
| | [raci-template.md](stewardship/raci-template.md) | Eight filled-in RACI matrices for the real activity sets, plus how to resolve the "whose fault is the wrong number" dispute |
| **Metrics** | [cdo-kpi-framework.md](metrics/cdo-kpi-framework.md) | How to measure governance without measuring activity — with the vanity metric for each KPI and how each one gets gamed |
| **Lineage** | [lineage-capture-guide.md](lineage/lineage-capture-guide.md) | Capture approaches compared, the hard parts (BI tools, spreadsheets, dynamic SQL), why lineage decays, and a worked impact analysis |

---

## The runnable part

Rules are declared in YAML so the people accountable for them can author and
review them without reading Python:

```yaml
- id: CLI-VAL-002
  name: Client segment is a controlled value
  dimension: validity
  check: allowed_values
  column: client_segment
  params:
    values: [INSTITUTIONAL, WHOLESALE, RETAIL, PRIVATE_WEALTH]
  severity: ERROR
  owner: Client Data Steward
  description: >
    Segment drives reporting aggregation and suitability rules. An
    out-of-list value silently drops the client from segment reporting.
```

Run them:

```bash
pip install pyyaml
cd quality
python dq_engine.py --data sample_customers.csv --rules example_rules.yaml \
                    --quarantine quarantine.csv --json report.json
```

```
==============================================================================
  DATA QUALITY SCORECARD  |  sample_customers.csv
==============================================================================
  rows evaluated : 52
  clean          : 41
  quarantined    : 11
  row pass rate  : 78.85%

  RULE                       DIMENSION      SEV     FAILED    PASS%
  --------------------------------------------------------------------------
  CLI-CMP-001                completeness   ERROR        0 100.00%
!!CLI-CMP-002                completeness   ERROR        1  98.08%
!!CLI-VAL-002                validity       ERROR        1  98.08%
  CLI-VAL-005                validity       WARN         1  98.08%
!!CLI-ACC-001                accuracy       ERROR        2  96.15%
!!CLI-UNQ-001                uniqueness     ERROR        2  96.15%
!!CLI-TML-001                timeliness     ERROR        1  98.08%

GATE FAILED: row pass rate 78.85% below threshold 90.00%
```

Exit code 1 on a breach, so it drops straight into CI or a pipeline gate.

### Four opinions baked into the engine

1. **Every rule needs an owner.** The loader *rejects* a rule without one. A
   rule with no accountable owner is a report, not a control.
2. **Unknown counts as a failure.** A value that cannot be parsed fails, unless
   the rule is specifically about nullability. Treating "can't tell" as a pass
   is how suites end up reporting 100% on visibly broken data.
3. **WARN never quarantines.** If a warning diverted rows it would silently be
   a drop, and someone would lose data they were promised. In the run above,
   the malformed-email and short-LEI rows are flagged and pass through; only
   ERROR rows are quarantined.
4. **Row-level verdicts, not just a percentage.** Every quarantined row carries
   the list of rule ids it broke, so it can be triaged and replayed.

The sample data is deliberately seeded with one defect per rule — see the
comments in `quality/example_rules.yaml` for what each is meant to catch.

> For production use Great Expectations, Soda, dbt tests or your platform's
> native expectations. This engine exists to make the *shape* of the problem
> legible in ~400 readable lines.

---

## How to use this as a starting kit

If you are standing up a governance function, the order that tends to work:

1. **Pick a narrow, painful scope.** One domain, one reporting pack, one
   regulatory obligation. Enterprise-wide programmes die of their own weight.
2. **Seed the glossary from the top.** Take the twenty metrics on the reports
   your executives actually read and work backwards to definitions and owners.
   [business-glossary-template.md](glossary/business-glossary-template.md)
3. **Name real owners.** Use [raci-template.md](stewardship/raci-template.md) to
   get one accountable name per activity — the single most common failure is a
   steward who is a name on a slide.
4. **Make quality executable.** Convert the top ten known data problems into
   rules with owners and thresholds.
   [dq-rule-catalogue.md](quality/dq-rule-catalogue.md)
5. **Measure outcomes, not activity.** Decide the scorecard before you start, or
   you will end up reporting glossary term counts.
   [cdo-kpi-framework.md](metrics/cdo-kpi-framework.md)
6. **Capture lineage as a by-product**, not as a documentation task, or it will
   be stale within a quarter.
   [lineage-capture-guide.md](lineage/lineage-capture-guide.md)

Numbers in these documents — thresholds, cadences, team sizes — are starting
points to calibrate against your own baseline, not benchmarks. Where a figure
appears, the derivation is stated so you can redo it with your own data.

---

## Scope and honesty

This toolkit is deliberately platform-agnostic. Where a catalogue tool is
referenced, the pattern is described rather than a product's current feature
set, because those change faster than documentation does.

It is also not a substitute for the DMBOK, for your regulator's actual
requirements, or for legal advice on data protection. It is the practical layer
that sits underneath those.

## Contributing

Issues and pull requests welcome — especially additional quality rules for the
catalogue, and RACI rows for activities not yet covered.

## License

MIT — see [LICENSE](LICENSE). Use these templates freely, including
commercially; attribution appreciated but not required.
