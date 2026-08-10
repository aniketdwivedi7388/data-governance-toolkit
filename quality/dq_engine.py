#!/usr/bin/env python3
"""A small, dependency-light data-quality rule engine.

Rules are declared in YAML so that a data steward can author and review them
without reading Python. The engine evaluates them against a CSV file and emits
a scorecard plus the failing rows, and returns a non-zero exit code when the
gate is breached — so it works unchanged as a CI check or a pipeline gate.

    python dq_engine.py --data sample_customers.csv --rules example_rules.yaml
    python dq_engine.py --data d.csv --rules r.yaml --fail-under 0.98 --json out.json

Why this exists
---------------
Production teams should use Great Expectations, Soda, dbt tests or their
platform's native expectations. This engine is here to make the *shape* of the
problem legible: rules as reviewable data, severity that changes behaviour,
row-level verdicts rather than a single percentage, and a gate that can stop a
pipeline. Roughly 400 lines is enough to show all four.

Deliberate design choices
-------------------------
* **Unknown counts as failure.** A rule evaluated against a missing or
  unparseable value fails unless the rule is specifically about nullability.
  The alternative — treating "can't tell" as a pass — is how suites end up
  reporting 100% on visibly broken data.
* **WARN never quarantines.** If a warning diverted rows it would silently be a
  drop, and someone would lose data they were told they would keep.
* **Every rule needs an owner.** A rule without an accountable owner is a
  report, not a control; the loader rejects rules that lack one.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

LOGGER = logging.getLogger("dq")

try:  # PyYAML is the only third-party dependency, and it is optional.
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
SEVERITIES = ("ERROR", "WARN")

DIMENSIONS = (
    "completeness",
    "validity",
    "accuracy",
    "consistency",
    "uniqueness",
    "timeliness",
)


@dataclass(frozen=True)
class Rule:
    """One declarative data-quality rule.

    Attributes
    ----------
    id:
        Stable identifier used in reports and in the row-level failure list.
        Never renumber these: dashboards and issue tickets reference them.
    dimension:
        One of :data:`DIMENSIONS`. Used to roll results up for reporting.
    owner:
        Accountable role or named steward. Required — see module docstring.
    severity:
        ``ERROR`` participates in the gate and quarantines rows; ``WARN`` is
        recorded and trended only.
    threshold:
        Optional per-rule minimum pass rate (0..1). When absent, any ERROR
        failure counts toward the global gate only.
    """

    id: str
    name: str
    check: str
    dimension: str = "validity"
    column: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    severity: str = "ERROR"
    owner: str = ""
    description: str = ""
    threshold: float | None = None

    def __post_init__(self) -> None:
        if self.check != UNIQUE_CHECK and self.check not in CHECKS:
            available = sorted(list(CHECKS) + [UNIQUE_CHECK])
            raise ValueError(
                f"Rule {self.id}: unknown check {self.check!r}. Available: {available}"
            )
        if self.severity not in SEVERITIES:
            raise ValueError(f"Rule {self.id}: severity must be one of {SEVERITIES}")
        if self.dimension not in DIMENSIONS:
            raise ValueError(f"Rule {self.id}: dimension must be one of {DIMENSIONS}")
        if not self.owner:
            raise ValueError(
                f"Rule {self.id}: 'owner' is required. A rule without an accountable "
                "owner is a report, not a control."
            )
        if self.check == UNIQUE_CHECK:
            if not self.column and not self.params.get("columns"):
                raise ValueError(
                    f"Rule {self.id}: 'unique' needs either a column or params.columns"
                )
        elif CHECKS[self.check].needs_column and not self.column:
            raise ValueError(f"Rule {self.id}: check {self.check!r} requires a column")


@dataclass
class RuleResult:
    rule: Rule
    rows_checked: int
    rows_failed: int

    @property
    def pass_rate(self) -> float:
        return 1.0 if self.rows_checked == 0 else 1 - (self.rows_failed / self.rows_checked)

    @property
    def breached(self) -> bool:
        """True when this rule's own threshold is breached."""
        if self.rule.threshold is None:
            return self.rows_failed > 0 and self.rule.severity == "ERROR"
        return self.pass_rate < self.rule.threshold


# ---------------------------------------------------------------------------
# Check implementations
#
# Each returns True when the value/row SATISFIES the rule.
# `value` is the raw string from the CSV; `row` is the whole record so that
# cross-column rules can be expressed.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Check:
    fn: Callable[[str | None, dict[str, str], dict[str, Any]], bool]
    needs_column: bool = True
    doc: str = ""


def _is_blank(value: str | None) -> bool:
    return value is None or str(value).strip() == ""


def _to_float(value: str | None) -> float | None:
    if _is_blank(value):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _to_date(value: str | None, fmts: Sequence[str]) -> datetime | None:
    if _is_blank(value):
        return None
    text = str(value).strip()
    for fmt in fmts:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y")


def _c_not_null(v, row, p):
    return not _is_blank(v)


def _c_not_blank(v, row, p):
    return not _is_blank(v)


def _c_allowed_values(v, row, p):
    values = p.get("values") or []
    if p.get("case_insensitive"):
        return not _is_blank(v) and str(v).strip().upper() in {str(x).upper() for x in values}
    return not _is_blank(v) and str(v).strip() in {str(x) for x in values}


def _c_regex(v, row, p):
    pattern = p.get("pattern")
    if not pattern:
        raise ValueError("regex check requires 'pattern'")
    return not _is_blank(v) and re.fullmatch(pattern, str(v).strip()) is not None


def _c_length_between(v, row, p):
    if _is_blank(v):
        return False
    n = len(str(v).strip())
    lo, hi = p.get("min", 0), p.get("max", 10**9)
    return lo <= n <= hi


def _c_numeric(v, row, p):
    return _to_float(v) is not None


def _c_range(v, row, p):
    num = _to_float(v)
    if num is None:
        return False
    lo, hi = p.get("min"), p.get("max")
    if lo is not None and num < float(lo):
        return False
    if hi is not None and num > float(hi):
        return False
    return True


def _c_is_date(v, row, p):
    return _to_date(v, p.get("formats") or DATE_FORMATS) is not None


def _c_not_future(v, row, p):
    dt = _to_date(v, p.get("formats") or DATE_FORMATS)
    if dt is None:
        return False
    tolerance = timedelta(minutes=int(p.get("tolerance_minutes", 0)))
    return dt <= datetime.now() + tolerance


def _c_date_order(v, row, p):
    """`column` must be on or after `params.after_column`."""
    other = p.get("after_column")
    if not other:
        raise ValueError("date_order requires 'after_column'")
    fmts = p.get("formats") or DATE_FORMATS
    a, b = _to_date(v, fmts), _to_date(row.get(other), fmts)
    if a is None or b is None:
        return False
    return a >= b


def _c_conditional_not_null(v, row, p):
    """`column` must be populated when `when_column` equals `when_value`."""
    when_col, when_val = p.get("when_column"), p.get("when_value")
    if not when_col:
        raise ValueError("conditional_not_null requires 'when_column'")
    if str(row.get(when_col, "")).strip() != str(when_val):
        return True  # condition not met -> rule does not apply
    return not _is_blank(v)


def _c_matches_column(v, row, p):
    other = p.get("other_column")
    if not other:
        raise ValueError("matches_column requires 'other_column'")
    return str(v or "").strip() == str(row.get(other, "")).strip()


CHECKS: dict[str, _Check] = {
    "not_null": _Check(_c_not_null, doc="Value is present."),
    "not_blank": _Check(_c_not_blank, doc="Value is present and not whitespace."),
    "allowed_values": _Check(_c_allowed_values, doc="Value is in a controlled list."),
    "regex": _Check(_c_regex, doc="Value fully matches a pattern."),
    "length_between": _Check(_c_length_between, doc="String length within bounds."),
    "numeric": _Check(_c_numeric, doc="Value parses as a number."),
    "range": _Check(_c_range, doc="Numeric value within bounds."),
    "is_date": _Check(_c_is_date, doc="Value parses as a date."),
    "not_future": _Check(_c_not_future, doc="Date is not in the future."),
    "date_order": _Check(_c_date_order, doc="Date is on/after another column."),
    "conditional_not_null": _Check(
        _c_conditional_not_null, doc="Populated when another column has a given value."
    ),
    "matches_column": _Check(_c_matches_column, doc="Equals another column."),
}

# Uniqueness is a set-level property, not a row-level one, so it is handled
# separately rather than shoehorned into the row-wise check registry.
UNIQUE_CHECK = "unique"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_rules(path: Path) -> tuple[list[Rule], dict[str, Any]]:
    """Load rules from YAML (preferred) or JSON.

    Returns ``(rules, metadata)`` where metadata carries dataset-level settings
    such as the primary key and the global gate threshold.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise SystemExit(
                "PyYAML is required to read YAML rule files.\n"
                "  pip install pyyaml     (or convert your rules to .json)"
            )
        doc = yaml.safe_load(text)
    else:
        doc = json.loads(text)

    if not isinstance(doc, dict) or "rules" not in doc:
        raise ValueError(f"{path}: expected a mapping with a top-level 'rules' key")

    meta = {k: v for k, v in doc.items() if k != "rules"}
    rules = []
    seen: set[str] = set()
    for raw in doc["rules"]:
        rule = Rule(**raw)
        if rule.id in seen:
            raise ValueError(f"Duplicate rule id {rule.id!r}")
        seen.add(rule.id)
        rules.append(rule)
    return rules, meta


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def evaluate(
    rows: Sequence[dict[str, str]],
    rules: Sequence[Rule],
) -> tuple[list[RuleResult], list[dict[str, Any]]]:
    """Evaluate every rule against every row.

    Returns ``(results, tagged_rows)``. Each tagged row carries a
    ``_dq_failures`` list naming the rule ids it broke, and ``_dq_quarantined``
    indicating whether an ERROR rule was among them.
    """
    tagged: list[dict[str, Any]] = [dict(r, _dq_failures=[]) for r in rows]
    results: list[RuleResult] = []

    for rule in rules:
        failed = 0

        if rule.check == UNIQUE_CHECK:
            counts: dict[str, int] = {}
            keys = rule.params.get("columns") or [rule.column]
            for row in rows:
                key = "||".join(str(row.get(c, "")).strip() for c in keys)
                counts[key] = counts.get(key, 0) + 1
            for row, out in zip(rows, tagged):
                key = "||".join(str(row.get(c, "")).strip() for c in keys)
                if counts[key] > 1:
                    out["_dq_failures"].append(rule.id)
                    failed += 1
        else:
            fn = CHECKS[rule.check].fn
            for row, out in zip(rows, tagged):
                value = row.get(rule.column) if rule.column else None
                try:
                    ok = bool(fn(value, row, rule.params))
                except Exception as exc:  # a broken rule must not pass silently
                    LOGGER.error("Rule %s raised on a row: %s", rule.id, exc)
                    ok = False
                if not ok:
                    out["_dq_failures"].append(rule.id)
                    failed += 1

        results.append(RuleResult(rule=rule, rows_checked=len(rows), rows_failed=failed))

    error_ids = {r.id for r in rules if r.severity == "ERROR"}
    for out in tagged:
        out["_dq_quarantined"] = any(f in error_ids for f in out["_dq_failures"])

    return results, tagged


def build_report(
    dataset: str, results: Sequence[RuleResult], tagged: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    total = len(tagged)
    quarantined = sum(1 for r in tagged if r["_dq_quarantined"])
    by_dimension: dict[str, dict[str, int]] = OrderedDict()
    for res in results:
        bucket = by_dimension.setdefault(res.rule.dimension, {"rules": 0, "breached": 0})
        bucket["rules"] += 1
        bucket["breached"] += int(res.breached)

    return {
        "dataset": dataset,
        "evaluated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows_total": total,
        "rows_clean": total - quarantined,
        "rows_quarantined": quarantined,
        "row_pass_rate": 1.0 if total == 0 else (total - quarantined) / total,
        "by_dimension": by_dimension,
        "rules": [
            {
                "id": r.rule.id,
                "name": r.rule.name,
                "dimension": r.rule.dimension,
                "column": r.rule.column,
                "severity": r.rule.severity,
                "owner": r.rule.owner,
                "threshold": r.rule.threshold,
                "rows_checked": r.rows_checked,
                "rows_failed": r.rows_failed,
                "pass_rate": round(r.pass_rate, 6),
                "breached": r.breached,
            }
            for r in results
        ],
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render(report: dict[str, Any]) -> str:
    lines = [
        "",
        "=" * 78,
        f"  DATA QUALITY SCORECARD  |  {report['dataset']}",
        "=" * 78,
        f"  rows evaluated : {report['rows_total']}",
        f"  clean          : {report['rows_clean']}",
        f"  quarantined    : {report['rows_quarantined']}",
        f"  row pass rate  : {report['row_pass_rate']:.2%}",
        "",
        f"  {'RULE':<26} {'DIMENSION':<14} {'SEV':<6} {'FAILED':>7} {'PASS%':>8}  ",
        "  " + "-" * 74,
    ]
    for r in report["rules"]:
        flag = "  " if not r["breached"] else ("!!" if r["severity"] == "ERROR" else " ~")
        lines.append(
            f"{flag}{r['id']:<26} {r['dimension']:<14} {r['severity']:<6} "
            f"{r['rows_failed']:>7} {r['pass_rate']:>7.2%}"
        )
    lines.append("")
    lines.append("  by dimension:")
    for dim, stat in report["by_dimension"].items():
        lines.append(f"    {dim:<14} {stat['rules']:>2} rules, {stat['breached']} breached")
    lines.append("")
    return "\n".join(lines)


def write_quarantine(path: Path, tagged: Iterable[dict[str, Any]]) -> int:
    rows = [r for r in tagged if r["_dq_quarantined"]]
    if not rows:
        return 0
    fieldnames = [k for k in rows[0] if k != "_dq_quarantined"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["_dq_failures"] = ";".join(out["_dq_failures"])
            writer.writerow(out)
    return len(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate declarative data-quality rules against a CSV file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit codes: 0 = pass, 1 = gate breached, 2 = configuration error.",
    )
    parser.add_argument("--data", required=True, type=Path, help="CSV file to evaluate")
    parser.add_argument("--rules", required=True, type=Path, help="YAML or JSON rule file")
    parser.add_argument("--fail-under", type=float, default=None,
                        help="Fail when the row pass rate is below this (0..1). "
                             "Overrides 'fail_under' in the rule file.")
    parser.add_argument("--quarantine", type=Path, default=None,
                        help="Write failing rows to this CSV")
    parser.add_argument("--json", dest="json_out", type=Path, default=None,
                        help="Write the full report as JSON")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    try:
        rules, meta = load_rules(args.rules)
        rows = load_csv(args.data)
    except (OSError, ValueError, TypeError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    results, tagged = evaluate(rows, rules)
    report = build_report(args.data.name, results, tagged)

    if not args.quiet:
        print(render(report))

    if args.quarantine:
        n = write_quarantine(args.quarantine, tagged)
        print(f"  quarantine written: {n} rows -> {args.quarantine}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  report written: {args.json_out}")

    threshold = args.fail_under if args.fail_under is not None else meta.get("fail_under")
    breached_rules = [r for r in results if r.breached and r.rule.severity == "ERROR"]

    if threshold is not None and report["row_pass_rate"] < float(threshold):
        print(
            f"\nGATE FAILED: row pass rate {report['row_pass_rate']:.2%} "
            f"below threshold {float(threshold):.2%}",
            file=sys.stderr,
        )
        return 1
    if breached_rules and threshold is None:
        print(
            "\nGATE FAILED: ERROR rules breached -> "
            + ", ".join(r.rule.id for r in breached_rules),
            file=sys.stderr,
        )
        return 1

    if breached_rules:
        print(
            "  note: "
            + f"{len(breached_rules)} ERROR rule(s) had failures but the overall "
            + "pass rate is within tolerance; rows were quarantined for replay."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
