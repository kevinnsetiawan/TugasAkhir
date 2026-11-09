"""Aggregate the 22 exact-forwarded-request trials for the manuscript."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "runs_exact_1640" / "runs"
OUT_JSON = HERE / "runs_exact_1640" / "aggregate.json"
OUT_MD = HERE / "runs_exact_1640" / "aggregate.md"
AUDIT_JSON = HERE / "ground_truth_audit_independent_v2" / "independent_audit.json"
DETECTOR_JSON = HERE.parents[1] / "rl_pentest" / "results" / "detector_benchmark.json"


def mean_sd(values):
    return {
        "mean": round(statistics.mean(values), 2),
        "sd": round(statistics.stdev(values), 2) if len(values) > 1 else None,
        "min": min(values),
        "max": max(values),
    }
def main():
    runs = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(RUN_DIR.glob("*.json"))]
    groups = {}
    for row in runs:
        groups.setdefault(row["mode"], []).append(row)
    summary = {
        "suite": "detector_blind_oracle_exact_target_request_budget_v2",
        "run_count": len(runs),
        "request_budget_per_run": 1640,
        "all_runs_exact": all(row["total_requests_forwarded_to_target"] == 1640 for row in runs),
        "runs_with_over_budget_rejections": sum(row["over_budget_requests_rejected_at_proxy"] > 0 for row in runs),
        "methods": {},
    }
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    detector = json.loads(DETECTOR_JSON.read_text(encoding="utf-8"))
    truth = {index: "positive" for index in audit["positive_action_indices"]}
    truth.update({index: "negative" for index in audit["negative_action_indices"]})
    truth.update({index: "unknown" for index in audit["unknown_action_indices"]})
    positives = {i for i, y in truth.items() if y == "positive"}
    negatives = {i for i, y in truth.items() if y == "negative"}
    unknowns = {i for i, y in truth.items() if y == "unknown"}
    predictions = {row["action_index"]: bool(row.get("verified") and row["predicted"] != "none") for row in detector["rows"]}
    confusion = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for action_index, label in truth.items():
        if label == "unknown":
            continue
        predicted_positive = predictions[action_index]
        if label == "positive" and predicted_positive:
            confusion["tp"] += 1
        elif label == "positive":
            confusion["fn"] += 1
        elif predicted_positive:
            confusion["fp"] += 1
        else:
            confusion["tn"] += 1
    tp, fp, fn = confusion["tp"], confusion["fp"], confusion["fn"]
    confusion["precision"] = round(tp / (tp + fp), 4) if tp + fp else 0.0
    confusion["recall"] = round(tp / (tp + fn), 4) if tp + fn else 0.0
    confusion["f1"] = round(2 * tp / (2 * tp + fp + fn), 4) if 2 * tp + fp + fn else 0.0
    summary["independent_oracle_detector_rescore"] = {
        "detector_prediction_source": "rl_pentest/results/detector_benchmark.json; predictions rescored without using its old confusion matrix",
        "ground_truth_audit_id": audit["audit_id"],
        "positive": sum(label == "positive" for label in truth.values()),
        "negative": sum(label == "negative" for label in truth.values()),
        "unknown_excluded": sum(label == "unknown" for label in truth.values()),
        "confusion": confusion,
        "caveat": "Detector-blind direct evidence was used for the author-run audit, but there was no external second reviewer; report consistency with this curated set, not independent accuracy or generalization.",
    }
    for mode, items in groups.items():
        counts = [row["verified_action_count"] for row in items]
        discovered_sets = [set(row["verified_actions"]) for row in items]
        true_positives = [len(found & positives) for found in discovered_sets]
        false_positives = [len(found & negatives) for found in discovered_sets]
        unresolved = [len(found & unknowns) for found in discovered_sets]
        missed = [len(positives - found) for found in discovered_sets]
        episodes = [row["primary_episodes"] for row in items]
        coverage = [row["independent_oracle_full_coverage_episode"] for row in items]
        unique = [row["unique_actions_visited"] for row in items]
        summary["methods"][mode] = {
            "n": len(items),
            "verified_action_count": mean_sd(counts),
            "oracle_true_positive_count": mean_sd(true_positives),
            "oracle_false_positive_count": mean_sd(false_positives),
            "verified_unknown_count": mean_sd(unresolved),
            "oracle_missed_positive_count": mean_sd(missed),
            "full_oracle_coverage_runs": sum(value is not None for value in coverage),
            "full_oracle_coverage_episode": mean_sd([value for value in coverage if value is not None]) if any(coverage) else None,
            "primary_episodes": mean_sd(episodes),
            "unique_actions_visited": mean_sd(unique),
            "full_action_space_enumeration_runs": sum(value == 120 for value in unique),
            "mean_duration_seconds": round(statistics.mean(row["training_duration_seconds"] for row in items), 2),
            "all_requests_exact": all(row["budget_exactly_used"] for row in items),
            "false_positive_action_sets": [sorted(found & negatives) for found in discovered_sets],
            "verified_unknown_action_sets": [sorted(found & unknowns) for found in discovered_sets],
            "missed_positive_action_sets": [sorted(positives - found) for found in discovered_sets],
        }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = ["# Exact 1,640 forwarded-request experiment summary", "", f"Runs: {summary['run_count']}", "", "| Method | n | Verified actions (mean; range) | Oracle TP (mean; range) | FP on labelled negatives | Verified unknown | Full coverage | Primary episodes (mean) | Unique actions (mean) | Exact budget |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|"]
    for mode, values in summary["methods"].items():
        c = values["verified_action_count"]
        p = values["oracle_true_positive_count"]
        f = values["oracle_false_positive_count"]
        unk = values["verified_unknown_count"]
        e = values["primary_episodes"]
        u = values["unique_actions_visited"]
        lines.append(
            f"| {mode} | {values['n']} | {c['mean']:.2f}; {c['min']}--{c['max']} "
            f"| {p['mean']:.2f}; {p['min']}--{p['max']} "
            f"| {f['mean']:.2f} | {unk['mean']:.2f} "
            f"| {values['full_oracle_coverage_runs']}/{values['n']} "
            f"| {e['mean']:.1f} | {u['mean']:.1f} | {values['all_requests_exact']} |"
        )
    lines += ["", f"All runs exact: {summary['all_runs_exact']}.", f"Runs with requests rejected locally after the budget: {summary['runs_with_over_budget_rejections']}.", "", "## Detector rescore against detector-blind audit", "", json.dumps(summary["independent_oracle_detector_rescore"], indent=2), ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
