# Table III reconciliation

This file checks whether Table III in `paper_revised.tex` is supported by the archived runs. It is generated from `tmp/icicyta_revision/evidence_manifest.json`.

## Verdict

Table III is **reproduced exactly** from 22 run JSON files under `tmp/icicyta_revision/runs/runs/`. Each run also has a 1,585-row CSV and a pair of Juice Shop server logs. The directory is untracked in git and absent from the zip backups, which is why a git/zip-only search does not find it.

## Aggregate check

| Method | n | Mean verified (SD); range | All 14 | Episode to all 14 | Mean requests |
|---|---:|---|---:|---:|---:|
| Q-Learning | 5 | 12.80 (1.10); 11-14 | 1/5 | 787.0 | 1634.2 |
| Random | 5 | 14.00 (0.00); 14-14 | 5/5 | 308.4 | 1639.2 |
| Fixed order | 1 | 14.00 (-); 14-14 | 1/1 | 66.0 | 1639.0 |
| QL without verification reward | 5 | 13.00 (1.22); 11-14 | 2/5 | 989.0 | 1635.6 |
| Lower reward | 3 | 13.33 (0.58); 13-14 | 1/3 | 787.0 | 1637.0 |
| Higher reward | 3 | 13.33 (0.58); 13-14 | 1/3 | 787.0 | 1636.7 |

These values match Table III in `paper_revised.tex` line by line.

## Per-seed evidence

| Method | Seed | Verified | Episode all 14 | Requests | JSON | CSV rows |
|---|---:|---:|---:|---:|---|---:|
| Q-Learning | 42 | 14 | 787 | 1640 | `runs\runs\01_ql_seed42.json` | 1585 |
| Q-Learning | 43 | 13 | - | 1637 | `runs\runs\02_ql_seed43.json` | 1585 |
| Q-Learning | 44 | 13 | - | 1634 | `runs\runs\03_ql_seed44.json` | 1585 |
| Q-Learning | 45 | 13 | - | 1629 | `runs\runs\04_ql_seed45.json` | 1585 |
| Q-Learning | 46 | 11 | - | 1631 | `runs\runs\05_ql_seed46.json` | 1585 |
| Random | 42 | 14 | 350 | 1639 | `runs\runs\06_random_seed42.json` | 1585 |
| Random | 43 | 14 | 440 | 1639 | `runs\runs\07_random_seed43.json` | 1585 |
| Random | 44 | 14 | 278 | 1640 | `runs\runs\08_random_seed44.json` | 1585 |
| Random | 45 | 14 | 257 | 1639 | `runs\runs\09_random_seed45.json` | 1585 |
| Random | 46 | 14 | 217 | 1639 | `runs\runs\10_random_seed46.json` | 1585 |
| Fixed order | 42 | 14 | 66 | 1639 | `runs\runs\11_fixed_seed42.json` | 1585 |
| QL without verification reward | 42 | 14 | 816 | 1639 | `runs\runs\12_ql_no_verify_reward_seed42.json` | 1585 |
| QL without verification reward | 43 | 13 | - | 1637 | `runs\runs\13_ql_no_verify_reward_seed43.json` | 1585 |
| QL without verification reward | 44 | 14 | 1162 | 1639 | `runs\runs\14_ql_no_verify_reward_seed44.json` | 1585 |
| QL without verification reward | 45 | 13 | - | 1632 | `runs\runs\15_ql_no_verify_reward_seed45.json` | 1585 |
| QL without verification reward | 46 | 11 | - | 1631 | `runs\runs\16_ql_no_verify_reward_seed46.json` | 1585 |
| Lower reward | 42 | 14 | 787 | 1640 | `runs\runs\17_ql_reward_low_seed42.json` | 1585 |
| Lower reward | 43 | 13 | - | 1637 | `runs\runs\18_ql_reward_low_seed43.json` | 1585 |
| Lower reward | 44 | 13 | - | 1634 | `runs\runs\19_ql_reward_low_seed44.json` | 1585 |
| Higher reward | 42 | 14 | 787 | 1639 | `runs\runs\20_ql_reward_high_seed42.json` | 1585 |
| Higher reward | 43 | 13 | - | 1637 | `runs\runs\21_ql_reward_high_seed43.json` | 1585 |
| Higher reward | 44 | 13 | - | 1634 | `runs\runs\22_ql_reward_high_seed44.json` | 1585 |

## Cross-check against the original single run

`dataset/ql/summary_ql.json` (the original seed-42 run) records 14 verified actions and `episode_all_discovered = 787`. The new `01_ql_seed42` run records the same 14 actions in the same verification order and the same episode (787). The action-index sequence is identical in 1,547 of 1,585 positions (97.6%); the remaining differences are consistent with timing-dependent browser verification. This is the expected signature of a genuine rerun, not a copied aggregate.

## Important caveat

`paper_revised.tex` uses this 22-run, 1,585-episode protocol. A separate newer experiment (`runs_exact_1640`, 26 runs, exactly 1,640 forwarded requests) gives different Q-Learning numbers (mean 11.40; 0/5 full coverage). Do not mix the two protocols in one table. Decide which protocol the submission uses and regenerate the table from that protocol only.

## Evidence durability

- `tmp/icicyta_revision/` is untracked (`git status` shows `??`), so it is invisible from GitHub and from the zip backups.
- `conference_paper_revised.tex` is tracked in git HEAD but deleted in the working tree; `paper_revised.tex` is untracked.
- Commit or archive `tmp/icicyta_revision/` (with hashes) before submission, or the evidence trail will not survive a fresh clone.
