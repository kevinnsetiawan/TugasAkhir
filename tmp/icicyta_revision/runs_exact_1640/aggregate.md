# Exact 1,640 forwarded-request experiment summary

Runs: 26

| Method | n | Verified actions (mean; range) | Oracle TP (mean; range) | FP on labelled negatives | Verified unknown | Full coverage | Primary episodes (mean) | Unique actions (mean) | Exact budget |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| ql | 5 | 11.40; 10--13 | 10.80; 9--12 | 0.60 | 0.00 | 0/5 | 865.0 | 71.4 | True |
| random | 5 | 14.00; 14--14 | 13.00; 13--13 | 1.00 | 0.00 | 5/5 | 569.6 | 119.2 | True |
| fixed | 5 | 14.00; 14--14 | 13.00; 13--13 | 1.00 | 0.00 | 5/5 | 584.8 | 120.0 | True |
| ql_no_verify_reward | 5 | 11.80; 10--13 | 11.20; 10--12 | 0.60 | 0.00 | 0/5 | 851.4 | 75.0 | True |
| ql_reward_low | 3 | 11.33; 10--13 | 10.67; 9--12 | 0.67 | 0.00 | 0/3 | 803.3 | 71.7 | True |
| ql_reward_high | 3 | 11.33; 10--13 | 10.67; 9--12 | 0.67 | 0.00 | 0/3 | 803.7 | 71.7 | True |

All runs exact: True.
Runs with requests rejected locally after the budget: 5.

## Detector rescore against detector-blind audit

{
  "detector_prediction_source": "rl_pentest/results/detector_benchmark.json; predictions rescored without using its old confusion matrix",
  "ground_truth_audit_id": "official_challenge_and_direct_effect_v2",
  "positive": 13,
  "negative": 69,
  "unknown_excluded": 38,
  "confusion": {
    "tp": 13,
    "fp": 0,
    "fn": 0,
    "tn": 69,
    "precision": 1.0,
    "recall": 1.0,
    "f1": 1.0
  },
  "caveat": "Detector-blind direct evidence was used for the author-run audit, but there was no external second reviewer; report consistency with this curated set, not independent accuracy or generalization."
}
