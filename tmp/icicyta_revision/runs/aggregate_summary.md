# Revision experiment aggregate

Each run used 1,585 primary action episodes. Total requests include eight benign baseline probes and the actual control/browser verification requests. All strategies used the same endpoint/payload space, verified-action mask, and final verification procedure; the reward ablation changes the reward signal only.

| Method | n | Mean verified actions (SD) | Range | All 14 | Mean episode to all 14* | Mean total requests | Mean run time (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| ql | 5 | 12.80 (1.10) | 11–14 | 1/5 | 787.0 | 1634.2 | 152.0 |
| random | 5 | 14.00 (0.00) | 14–14 | 5/5 | 308.4 | 1639.2 | 201.5 |
| fixed | 1 | 14.00 (—) | 14–14 | 1/1 | 66.0 | 1639.0 | 199.4 |
| ql_no_verify_reward | 5 | 13.00 (1.22) | 11–14 | 2/5 | 989.0 | 1635.6 | 175.6 |
| ql_reward_low | 3 | 13.33 (0.58) | 13–14 | 1/3 | 787.0 | 1637.0 | 156.1 |
| ql_reward_high | 3 | 13.33 (0.58) | 13–14 | 1/3 | 787.0 | 1636.7 | 141.5 |

*Mean episode to all 14 is calculated only among runs that found all 14. For fixed-order scan, n=1.

## Per-run values

| Run | Seed | Verified actions | SQLi | XSS | File/fuzzing | Episode all 14 | Total requests | Seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ql | 42 | 14 | 6 | 5 | 3 | 787 | 1640 | 148.0 |
| ql | 43 | 13 | 6 | 5 | 2 | — | 1637 | 138.6 |
| ql | 44 | 13 | 6 | 5 | 2 | — | 1634 | 137.0 |
| ql | 45 | 13 | 6 | 4 | 3 | — | 1629 | 152.9 |
| ql | 46 | 11 | 6 | 4 | 1 | — | 1631 | 183.7 |
| random | 42 | 14 | 6 | 5 | 3 | 350 | 1639 | 199.8 |
| random | 43 | 14 | 6 | 5 | 3 | 440 | 1639 | 213.8 |
| random | 44 | 14 | 6 | 5 | 3 | 278 | 1640 | 202.0 |
| random | 45 | 14 | 6 | 5 | 3 | 257 | 1639 | 196.8 |
| random | 46 | 14 | 6 | 5 | 3 | 217 | 1639 | 195.3 |
| fixed | 42 | 14 | 6 | 5 | 3 | 66 | 1639 | 199.4 |
| ql_no_verify_reward | 42 | 14 | 6 | 5 | 3 | 816 | 1639 | 172.9 |
| ql_no_verify_reward | 43 | 13 | 6 | 5 | 2 | — | 1637 | 188.2 |
| ql_no_verify_reward | 44 | 14 | 6 | 5 | 3 | 1162 | 1639 | 205.2 |
| ql_no_verify_reward | 45 | 13 | 6 | 4 | 3 | — | 1632 | 133.5 |
| ql_no_verify_reward | 46 | 11 | 6 | 4 | 1 | — | 1631 | 178.4 |
| ql_reward_low | 42 | 14 | 6 | 5 | 3 | 787 | 1640 | 189.9 |
| ql_reward_low | 43 | 13 | 6 | 5 | 2 | — | 1637 | 144.3 |
| ql_reward_low | 44 | 13 | 6 | 5 | 2 | — | 1634 | 134.2 |
| ql_reward_high | 42 | 14 | 6 | 5 | 3 | 787 | 1639 | 149.1 |
| ql_reward_high | 43 | 13 | 6 | 5 | 2 | — | 1637 | 145.9 |
| ql_reward_high | 44 | 13 | 6 | 5 | 2 | — | 1634 | 129.6 |

## Reward variants

Base: +50 verified / +10 anomaly / -1 normal / -5 request error. Low: +25 / +5 / -1 / -5. High: +100 / +20 / -1 / -5. Length bonuses were unchanged. Reward variants used seeds 42, 43, and 44.

## Interpretation limits

The 14-action reference comes from the existing curated set and is not an independent oracle. The no-verification-reward ablation still uses verification for recording and action masking. These runs therefore compare policies within the current implementation; they do not resolve the reviewer request for independent manual ground truth.
