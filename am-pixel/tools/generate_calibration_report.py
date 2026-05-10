#!/usr/bin/env python3.14
"""
tools/generate_calibration_report.py
======================================
Generates logs/rubric_calibration_report.md from curation_log.jsonl.
Run after a curation session to get rubric calibration data.

Usage:
  python tools/generate_calibration_report.py
"""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
REVIEW_DIR   = PROJECT_ROOT / "data" / "golden_review"
SCORES_PATH  = REVIEW_DIR / "scores.json"
CUR_LOG      = REVIEW_DIR / "curation_log.jsonl"
REPORT_PATH  = PROJECT_ROOT / "logs" / "rubric_calibration_report.md"


def main() -> None:
    if not CUR_LOG.exists() or CUR_LOG.stat().st_size == 0:
        print("No curation log found. Run curation_ui.py first.")
        return

    # Load scores index
    scores_idx: dict[str, dict] = {}
    if SCORES_PATH.exists():
        for e in json.loads(SCORES_PATH.read_text()):
            scores_idx[e["sprite_id"]] = e

    # Load curation log
    decisions: list[dict] = []
    for line in CUR_LOG.read_text().splitlines():
        try:
            decisions.append(json.loads(line))
        except Exception:
            pass

    # Aggregate
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for d in decisions:
        by_bucket[d["bucket"]].append(d)

    rubric_pass_human_reject: list[dict] = []   # rubric said pass, human said no
    rubric_fail_human_accept: list[dict] = []   # rubric said fail, human said yes
    flagged_for_recalibration: list[dict] = []

    for d in decisions:
        sid = d["sprite_id"]
        score_entry = scores_idx.get(sid, {})
        rubric_score = score_entry.get("total_score", d.get("rubric_scores_at_decision", {}).get("total_score", -1))
        rubric_passed = rubric_score >= 85

        if d["decision"] == "reject" and rubric_passed:
            rubric_pass_human_reject.append({**d, "total_score": rubric_score,
                                              "failure_modes": score_entry.get("primary_failure_modes", [])})
        elif d["decision"] == "accept" and not rubric_passed:
            rubric_fail_human_accept.append({**d, "total_score": rubric_score,
                                              "failure_modes": score_entry.get("primary_failure_modes", [])})
        elif d["decision"] == "flag_recalibration":
            flagged_for_recalibration.append({**d, "total_score": rubric_score})

    # Group too-permissive by failure mode
    permissive_by_mode: dict[str, int] = defaultdict(int)
    for d in rubric_pass_human_reject:
        for fm in d["failure_modes"] or ["no_flag"]:
            permissive_by_mode[fm] += 1

    # Group too-strict by failure mode
    strict_by_mode: dict[str, int] = defaultdict(int)
    for d in rubric_fail_human_accept:
        for fm in d["failure_modes"] or ["no_flag"]:
            strict_by_mode[fm] += 1

    # Write report
    lines = [
        "# Rubric Calibration Report",
        f"",
        f"Generated: {datetime.now().isoformat()}",
        f"Curation sessions contributing: {len(set(d.get('session_id','?') for d in decisions))}",
        f"",
        "---",
        "",
        "## Review Summary by Bucket",
        "",
        "| Bucket | Reviewed | Accepted | Rejected | Flagged | Accept Rate |",
        "|--------|----------|----------|----------|---------|-------------|" ,
    ]
    for bucket, items in sorted(by_bucket.items()):
        acc = sum(1 for d in items if d["decision"] == "accept")
        rej = sum(1 for d in items if d["decision"] == "reject")
        flg = sum(1 for d in items if d["decision"] == "flag_recalibration")
        rate = f"{acc/len(items)*100:.0f}%" if items else "—"
        lines.append(f"| {bucket} | {len(items)} | {acc} | {rej} | {flg} | {rate} |")
    lines += ["", "---", ""]

    lines += [
        "## Rubric Too Permissive — Passed Rubric, Human Rejected",
        "",
        f"**Total: {len(rubric_pass_human_reject)}**",
        "",
    ]
    if permissive_by_mode:
        lines.append("Grouped by primary failure mode:")
        lines.append("")
        for mode, cnt in sorted(permissive_by_mode.items(), key=lambda x: -x[1]):
            lines.append(f"- `{mode}`: {cnt} sprites")
    else:
        lines.append("_None — rubric and human judgement aligned on all passes._")
    lines += ["", "---", ""]

    lines += [
        "## Rubric Too Strict — Failed Rubric, Human Accepted",
        "",
        f"**Total: {len(rubric_fail_human_accept)}**",
        "",
    ]
    if strict_by_mode:
        lines.append("Grouped by failure mode that triggered deduction:")
        lines.append("")
        for mode, cnt in sorted(strict_by_mode.items(), key=lambda x: -x[1]):
            lines.append(f"- `{mode}`: {cnt} sprites")
    else:
        lines.append("_None — rubric and human judgement aligned on all failures._")
    lines += ["", "---", ""]

    lines += [
        "## Flagged for Recalibration",
        "",
        f"**Total: {len(flagged_for_recalibration)}**",
        "",
    ]
    for d in flagged_for_recalibration:
        note = d.get("notes", "").strip()
        lines.append(f"- `{d['sprite_id']}` (score {d.get('total_score','?')}, bucket {d['bucket']}): {note or '(no notes)'}")
    lines += ["", "---", ""]

    lines += [
        "## Suggested Threshold Adjustments",
        "",
        "*Auto-generated suggestions based on disagreement patterns.*",
        "*Do NOT apply without reviewing — these are observations, not directives.*",
        "",
    ]
    if len(rubric_pass_human_reject) > 10:
        top_mode = max(permissive_by_mode, key=permissive_by_mode.get) if permissive_by_mode else None
        if top_mode:
            lines.append(f"- **Consider tightening** deduction weight for `{top_mode}` "
                         f"({permissive_by_mode[top_mode]} rubric-passes rejected by human).")
    if len(rubric_fail_human_accept) > 10:
        top_mode = max(strict_by_mode, key=strict_by_mode.get) if strict_by_mode else None
        if top_mode:
            lines.append(f"- **Consider relaxing** deduction weight for `{top_mode}` "
                         f"({strict_by_mode[top_mode]} rubric-fails accepted by human).")
    if not rubric_pass_human_reject and not rubric_fail_human_accept:
        lines.append("_Insufficient data for suggestions — continue curation._")
    lines += ["", "---", ""]
    lines.append("*AM Pixel Rubric Calibration Report — input to EVALUATION_RUBRIC.md threshold review before Phase 4 training.*")

    REPORT_PATH.write_text("\n".join(lines))
    print(f"Report written to {REPORT_PATH}")
    print(f"  Reviewed: {len(decisions)} sprites")
    print(f"  Rubric too permissive: {len(rubric_pass_human_reject)}")
    print(f"  Rubric too strict:     {len(rubric_fail_human_accept)}")
    print(f"  Flagged:               {len(flagged_for_recalibration)}")


if __name__ == "__main__":
    main()
