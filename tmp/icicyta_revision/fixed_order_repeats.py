"""Add four fresh-instance replicas of the deterministic fixed-order baseline."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import exact_budget_runner as experiment

HERE = Path(__file__).resolve().parent
AUDIT_JSON = HERE / "ground_truth_audit_independent_v2" / "independent_audit.json"


def main():
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    positives = set(audit["positive_action_indices"])
    counter = experiment.RequestCounter(experiment.REQUEST_BUDGET)
    proxy = experiment.CountedProxy(experiment.PROXY_PORT, counter)
    thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    thread.start()
    try:
        for seed in (43, 44, 45, 46):
            run_id = f"fixed_order_replica_seed{seed}"
            print(f"Starting {run_id}", flush=True)
            server = experiment.JuiceShopProcess(run_id)
            server.start()
            try:
                with counter.lock:
                    counter.forwarded = 0
                    counter.rejected = 0
                experiment.run_trial("fixed", seed, run_id, counter, positives)
                if counter.forwarded != experiment.REQUEST_BUDGET:
                    raise RuntimeError(f"{run_id} stopped at {counter.forwarded} requests")
            finally:
                server.stop()
    finally:
        proxy.shutdown()
        proxy.server_close()
        thread.join(timeout=5)
    print("FIXED-ORDER REPLICAS COMPLETE", flush=True)


if __name__ == "__main__":
    main()
