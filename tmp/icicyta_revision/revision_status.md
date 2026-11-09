# ICICyTA 2026 revision status

## Added to the working LaTeX draft

- Clarified that the endpoint and payload space uses source-informed human prior and does not test endpoint discovery.
- Added a table of all 15 payload templates and explained the 8 × 15 pairing.
- Explained that each request's response summary becomes the next action-selection context, while no explicit application workflow state is modeled.
- Calculated the epsilon schedule: the floor is reached at episode 23; epsilon is at least 0.5 for the first seven episodes.
- Specified how attack-request failures and inconclusive control failures affect reward assignment.
- Described the implemented SQLi and file-disclosure evidence criteria, with a note that the old logs do not preserve response bodies or content types.
- Added two reconstructed XSS input/control examples and identified that the log stores final verdicts rather than raw navigation traces.
- Broke down the 14 actions across the five endpoint/class pairs.
- Added sensitivity results for the two extreme labels of the 46 unknown actions.
- Removed the prior-work results table and narrowed the generalization and contribution claims.

## New experiments completed

- 22 trials, each with 1,585 primary action episodes.
- Q-Learning and random selection: five seeds each (42--46).
- Fixed-order scan: one deterministic trial.
- Q-Learning without verification-guided reward: five seeds (42--46); verification remains active for reporting and action masking.
- Reward sensitivity: lower (+25/+5/-1/-5) and higher (+100/+20/-1/-5) settings, three paired seeds each (42--44); length bonus unchanged.
- Each trial used a freshly restarted Juice Shop 20.2.0 source instance on Windows/Node.js v24.22.1. The exact total HTTP interaction count varies slightly because control and browser verification requests vary.
- Per-run JSON/CSV, server logs, aggregate JSON/CSV/Markdown, and the experiment runner are under `tmp/icicyta_revision/runs/` and `tmp/icicyta_revision/`.

## Still required before a resubmission

1. Obtain an independent audit of the ground-truth labels; current comparisons use the same curated reference and verification procedure.
2. Capture representative SQLi/file response bodies and content types, and export raw per-navigation XSS canary/control traces. Existing CSVs preserve final verdicts but not those raw artifacts.
3. Consider increasing seed counts and matching the exact total HTTP request budget, including verification overhead. Current runs match the 1,585 primary-action budget; total interactions ranged from 1,629 to 1,640.
4. Confirm the original single-seed run's launch mode and host details. The new repeated runs used `node build/app.js`, Node.js v24.22.1, Windows, and Juice Shop 20.2.0.

The LaTeX draft was updated with the new results. Its detector metrics still do not constitute independent validation, so the manuscript is not yet ready for resubmission.
