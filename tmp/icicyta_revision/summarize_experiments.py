"""Aggregate the completed ICICyTA revision experiment suite."""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent / "runs" / "runs"
OUT = Path(__file__).resolve().parent / "runs"


def mean(values):
    return sum(values) / len(values) if values else None


def sample_sd(values):
    if len(values) < 2:
        return None
    avg = mean(values)
    return math.sqrt(sum((x - avg) ** 2 for x in values) / (len(values) - 1))


def main():
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(BASE.glob("*.json"))]
    groups = defaultdict(list)
    for run in runs:
        groups[run["mode"]].append(run)

    aggregate = {"n_runs": len(runs), "groups": {}}
    rows = []
    for mode in ("ql", "random", "fixed", "ql_no_verify_reward", "ql_reward_low", "ql_reward_high"):
        items = groups[mode]
        findings = [x["discovered_action_count"] for x in items]
        coverage_episodes = [x["episode_all_reference_positives_found"] for x in items
                             if x["episode_all_reference_positives_found"] is not None]
        requests = [x["total_requests_including_verification"] for x in items]
        durations = [x["training_duration_seconds"] for x in items]
        class_means = {}
        for class_name in ("sqli", "xss", "fuzzing"):
            class_means[class_name] = mean([x["per_class_verified_actions"].get(class_name, 0) for x in items])
        result = {
            "n": len(items),
            "seeds": [x["seed"] for x in items],
            "mean_verified_actions": mean(findings),
            "sample_sd_verified_actions": sample_sd(findings),
            "min_verified_actions": min(findings),
            "max_verified_actions": max(findings),
            "runs_finding_all_14": sum(x["discovered_action_count"] == 14 for x in items),
            "mean_episode_all_14_among_complete_runs": mean(coverage_episodes),
            "complete_run_episode_values": coverage_episodes,
            "mean_total_requests_including_verification": mean(requests),
            "mean_training_duration_seconds": mean(durations),
            "mean_verified_actions_by_class": class_means,
        }
        aggregate["groups"][mode] = result
        rows.append({"mode": mode, **result})

    aggregate["runs"] = runs
    (OUT / "aggregate_summary.json").write_text(
        json.dumps(aggregate, indent=2), encoding="utf-8"
    )

    flat = []
    for run in runs:
        flat.append({
            "run_id": run["run_id"],
            "mode": run["mode"],
            "seed": run["seed"],
            "verified_actions": run["discovered_action_count"],
            "sqli": run["per_class_verified_actions"].get("sqli", 0),
            "xss": run["per_class_verified_actions"].get("xss", 0),
            "file_disclosure_detector_fuzzing": run["per_class_verified_actions"].get("fuzzing", 0),
            "episode_all_14": run["episode_all_reference_positives_found"],
            "total_requests": run["total_requests_including_verification"],
            "duration_seconds": run["training_duration_seconds"],
            "cumulative_reward": run["cumulative_reward"],
        })
    with open(OUT / "per_run_results.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0].keys()))
        writer.writeheader()
        writer.writerows(flat)

    with open(OUT / "aggregate_summary.md", "w", encoding="utf-8") as handle:
        handle.write("# Revision experiment aggregate\n\n")
        handle.write("Each run used 1,585 primary action episodes. Total requests include eight benign baseline probes and the actual control/browser verification requests. All strategies used the same endpoint/payload space, verified-action mask, and final verification procedure; the reward ablation changes the reward signal only.\n\n")
        handle.write("| Method | n | Mean verified actions (SD) | Range | All 14 | Mean episode to all 14* | Mean total requests | Mean run time (s) |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for mode in ("ql", "random", "fixed", "ql_no_verify_reward", "ql_reward_low", "ql_reward_high"):
            x = aggregate["groups"][mode]
            sd = "—" if x["sample_sd_verified_actions"] is None else f"{x['sample_sd_verified_actions']:.2f}"
            mean_cov = "—" if x["mean_episode_all_14_among_complete_runs"] is None else f"{x['mean_episode_all_14_among_complete_runs']:.1f}"
            handle.write(
                f"| {mode} | {x['n']} | {x['mean_verified_actions']:.2f} ({sd}) | "
                f"{x['min_verified_actions']}–{x['max_verified_actions']} | "
                f"{x['runs_finding_all_14']}/{x['n']} | {mean_cov} | "
                f"{x['mean_total_requests_including_verification']:.1f} | "
                f"{x['mean_training_duration_seconds']:.1f} |\n"
            )
        handle.write("\n*Mean episode to all 14 is calculated only among runs that found all 14. For fixed-order scan, n=1.\n\n")
        handle.write("## Per-run values\n\n")
        handle.write("| Run | Seed | Verified actions | SQLi | XSS | File/fuzzing | Episode all 14 | Total requests | Seconds |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for x in flat:
            all14 = "—" if x["episode_all_14"] is None else x["episode_all_14"]
            handle.write(
                f"| {x['mode']} | {x['seed']} | {x['verified_actions']} | {x['sqli']} | "
                f"{x['xss']} | {x['file_disclosure_detector_fuzzing']} | {all14} | "
                f"{x['total_requests']} | {x['duration_seconds']:.1f} |\n"
            )
        handle.write("\n## Reward variants\n\n")
        handle.write("Base: +50 verified / +10 anomaly / -1 normal / -5 request error. Low: +25 / +5 / -1 / -5. High: +100 / +20 / -1 / -5. Length bonuses were unchanged. Reward variants used seeds 42, 43, and 44.\n")
        handle.write("\n## Interpretation limits\n\n")
        handle.write("The 14-action reference comes from the existing curated set and is not an independent oracle. The no-verification-reward ablation still uses verification for recording and action masking. These runs therefore compare policies within the current implementation; they do not resolve the reviewer request for independent manual ground truth.\n")

    print(json.dumps(aggregate["groups"], indent=2))


if __name__ == "__main__":
    main()
