"""Reproducible local experiment suite for the ICICyTA revision.

Writes every run under this directory and does not overwrite the project's
existing QL/DQN results. The Juice Shop process is restarted for each trial;
the application recreates its SQLite database on startup.
"""
from __future__ import annotations

import csv
import json
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "rl_pentest"
JUICE_SHOP = ROOT / "juice-shop"
OUT_DIR = Path(__file__).resolve().parent / "runs"
NODE = Path(r"C:\Users\Kevin Setiawan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe")
sys.path.insert(0, str(PROJECT))

from agent.q_learning_agent import QLearningAgent  # noqa: E402
from analyzer.browser_verifier import BrowserVerifier  # noqa: E402
from analyzer.response_analyzer import ResponseAnalyzer  # noqa: E402
from config import (  # noqa: E402
    ALPHA,
    BASE_URL,
    ENDPOINTS,
    EPSILON_DECAY,
    EPSILON_MIN,
    EPSILON_START,
    GAMMA,
    OPTIMISTIC_INIT,
    PAYLOADS_FILE,
    REQUEST_TIMEOUT,
    TOTAL_EPISODES,
    XSS_PAGES,
)
from engine.http_client import HTTPClient  # noqa: E402
from engine.payload_generator import PayloadGenerator  # noqa: E402
from ground_truth import expected_label  # noqa: E402
from reward.reward_system import RewardSystem  # noqa: E402
from training_loop import probe_endpoint_baselines, run_episode  # noqa: E402

SEEDS = [42, 43, 44, 45, 46]


class RandomPolicy:
    def __init__(self, n_actions: int):
        self.n_actions = n_actions

    def choose_action(self, _state, mask=None):
        allowed = [i for i in range(self.n_actions) if mask is None or i not in mask]
        return random.choice(allowed or list(range(self.n_actions)))

    def learn(self, *_args):
        pass

    def decay_exploration(self):
        pass


class FixedOrderPolicy:
    """Cycle through ascending action IDs, skipping verified findings."""

    def __init__(self, n_actions: int):
        self.n_actions = n_actions
        self.cursor = 0

    def choose_action(self, _state, mask=None):
        masked = mask or set()
        for offset in range(self.n_actions):
            action = (self.cursor + offset) % self.n_actions
            if action not in masked:
                self.cursor = (action + 1) % self.n_actions
                return action
        return 0

    def learn(self, *_args):
        pass

    def decay_exploration(self):
        pass


class RewardVariant(RewardSystem):
    def __init__(self, vulnerability: int, anomaly: int, normal: int = -1, error: int = -5):
        self.vulnerability_reward = vulnerability
        self.anomaly_reward = anomaly
        self.normal_reward = normal
        self.error_reward = error

    def compute_reward(self, analysis: dict, verified: bool = True) -> int:
        if analysis.get("request_error"):
            return self.error_reward
        vulnerability = analysis.get("vulnerability", "none")
        if vulnerability in {"sqli", "xss", "fuzzing"}:
            base = self.vulnerability_reward if verified else self.anomaly_reward
        elif analysis.get("error_flag") or analysis.get("reflected_flag") or analysis.get("significant_change"):
            base = self.anomaly_reward
        else:
            base = self.normal_reward
        return base + self._length_bonus(analysis)


class JuiceShopProcess:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.process = None
        self.stdout_handle = None
        self.stderr_handle = None

    def start(self):
        log_dir = OUT_DIR / "server_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.stdout_handle = open(log_dir / f"{self.run_id}.stdout.log", "wb")
        self.stderr_handle = open(log_dir / f"{self.run_id}.stderr.log", "wb")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.process = subprocess.Popen(
            [str(NODE), "build/app.js"],
            cwd=JUICE_SHOP,
            stdout=self.stdout_handle,
            stderr=self.stderr_handle,
            creationflags=creationflags,
        )
        deadline = time.monotonic() + 90
        last_error = None
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"Juice Shop exited early; see server log for {self.run_id}")
            try:
                response = requests.get(BASE_URL, timeout=3)
                if response.status_code == 200:
                    return
            except requests.RequestException as error:
                last_error = error
            time.sleep(1)
        raise TimeoutError(f"Juice Shop did not become ready: {last_error}")

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        for handle in (self.stdout_handle, self.stderr_handle):
            if handle is not None:
                handle.close()


def make_agent(mode: str, n_actions: int):
    if mode in {"ql", "ql_no_verify_reward", "ql_reward_low", "ql_reward_high"}:
        return QLearningAgent(
            n_actions=n_actions,
            alpha=ALPHA,
            gamma=GAMMA,
            epsilon=EPSILON_START,
            min_epsilon=EPSILON_MIN,
            decay=EPSILON_DECAY,
            qtable_file=None,
            optimistic_init=OPTIMISTIC_INIT,
        )
    if mode == "random":
        return RandomPolicy(n_actions)
    if mode == "fixed":
        return FixedOrderPolicy(n_actions)
    raise ValueError(f"Unknown mode: {mode}")


def make_reward_system(mode: str):
    if mode == "ql_reward_low":
        return RewardVariant(25, 5)
    if mode == "ql_reward_high":
        return RewardVariant(100, 20)
    return RewardSystem()


def run_trial(mode: str, seed: int, run_id: str):
    random.seed(seed)
    np.random.seed(seed)
    payload_generator = PayloadGenerator(PAYLOADS_FILE, n_endpoints=len(ENDPOINTS))
    n_actions = payload_generator.get_action_count()
    agent = make_agent(mode, n_actions)
    analyzer = ResponseAnalyzer()
    client = HTTPClient(BASE_URL, endpoints=ENDPOINTS, timeout=REQUEST_TIMEOUT)
    browser = BrowserVerifier(BASE_URL)
    reward_system = make_reward_system(mode)

    baseline_probes = probe_endpoint_baselines(client, analyzer)
    current_state = ("2xx", 1, 0, 0, 0, 0, 0, 0)
    discovered_actions: set[int] = set()
    verification_requests = 0
    total_reward = 0
    records = []
    first_discovery = None
    all_known_episode = None
    expected_positive_count = sum(
        expected_label(action) in {"sqli", "xss", "fuzzing"}
        for action in range(n_actions)
    )
    started = time.monotonic()

    for episode in range(1, TOTAL_EPISODES + 1):
        record, next_state, reward, verification_count = run_episode(
            agent,
            payload_generator,
            client,
            analyzer,
            reward_system,
            current_state,
            mask=set(discovered_actions),
            browser_verifier=browser,
            xss_pages=XSS_PAGES,
            verification_guided_reward=(mode != "ql_no_verify_reward"),
        )
        record["episode"] = episode
        records.append(record)
        current_state = next_state
        total_reward += reward
        verification_requests += verification_count
        if record["verified"] and record["vulnerability"] != "none":
            discovered_actions.add(record["action_index"])
            if first_discovery is None:
                first_discovery = episode
            if all_known_episode is None and len(discovered_actions) == expected_positive_count:
                all_known_episode = episode
        agent.decay_exploration()
        if episode % 500 == 0:
            print(f"{run_id}: episode {episode}/{TOTAL_EPISODES}", flush=True)

    duration = round(time.monotonic() - started, 2)
    browser_navigations = browser.navigations
    browser_warning = None if browser.available else browser.unavailable_reason
    browser.close()
    client.session.close()

    unique_locations = sorted({
        (row["endpoint_index"], row["vulnerability"])
        for row in records
        if row["verified"] and row["vulnerability"] != "none"
    })
    per_class = {}
    for row in records:
        if row["verified"] and row["vulnerability"] != "none":
            label = row["vulnerability"]
            per_class[label] = per_class.get(label, 0) + 1

    summary = {
        "run_id": run_id,
        "mode": mode,
        "seed": seed,
        "episodes": TOTAL_EPISODES,
        "action_count": n_actions,
        "expected_positive_actions_from_existing_reference": expected_positive_count,
        "discovered_action_count": len(discovered_actions),
        "discovered_actions": sorted(discovered_actions),
        "per_class_verified_actions": per_class,
        "unique_endpoint_class_pairs": len(unique_locations),
        "endpoint_class_pairs": [list(item) for item in unique_locations],
        "first_verified_episode": first_discovery,
        "episode_all_reference_positives_found": all_known_episode,
        "baseline_probe_requests": len(baseline_probes),
        "verification_requests": verification_requests,
        "browser_navigations": browser_navigations,
        "total_requests_including_verification": TOTAL_EPISODES + len(baseline_probes) + verification_requests,
        "cumulative_reward": total_reward,
        "training_duration_seconds": duration,
        "epsilon_decay": EPSILON_DECAY if mode in {"ql", "ql_no_verify_reward", "ql_reward_low", "ql_reward_high"} else None,
        "reward_setting": {
            "base": {"verified": 50, "anomaly": 10, "normal": -1, "error": -5},
            "ql_reward_low": {"verified": 25, "anomaly": 5, "normal": -1, "error": -5},
            "ql_reward_high": {"verified": 100, "anomaly": 20, "normal": -1, "error": -5},
        }.get(mode, {"verified": 50, "anomaly": 10, "normal": -1, "error": -5}),
        "verification_guided_reward": mode != "ql_no_verify_reward",
        "verification_still_used_for_reporting_and_action_masking": True,
        "browser_verifier_warning": browser_warning,
    }

    run_dir = OUT_DIR / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    with open(run_dir / f"{run_id}.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    if records:
        with open(run_dir / f"{run_id}.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
    print(json.dumps({k: summary[k] for k in (
        "run_id", "discovered_action_count", "per_class_verified_actions",
        "first_verified_episode", "episode_all_reference_positives_found",
        "total_requests_including_verification", "training_duration_seconds"
    )}, ensure_ascii=False), flush=True)


def build_plan():
    plan = []
    for seed in SEEDS:
        plan.append(("ql", seed))
    for seed in SEEDS:
        plan.append(("random", seed))
    plan.append(("fixed", 42))
    for seed in SEEDS:
        plan.append(("ql_no_verify_reward", seed))
    for seed in SEEDS[:3]:
        plan.append(("ql_reward_low", seed))
    for seed in SEEDS[:3]:
        plan.append(("ql_reward_high", seed))
    return plan


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    node_version = subprocess.check_output([str(NODE), "--version"], text=True).strip()
    print(json.dumps({
        "suite": "revision_experiments_v1",
        "runs": len(build_plan()),
        "seeds": SEEDS,
        "episodes_per_run": TOTAL_EPISODES,
        "node_version": node_version,
        "juice_shop_version": "20.2.0",
        "target": BASE_URL,
        "plan": build_plan(),
    }, indent=2), flush=True)

    for index, (mode, seed) in enumerate(build_plan(), start=1):
        run_id = f"{index:02d}_{mode}_seed{seed}"
        print(f"Starting {index}/{len(build_plan())}: {run_id}", flush=True)
        server = JuiceShopProcess(run_id)
        server.start()
        try:
            run_trial(mode, seed, run_id)
        finally:
            server.stop()

    print("EXPERIMENT SUITE COMPLETE", flush=True)


if __name__ == "__main__":
    main()
