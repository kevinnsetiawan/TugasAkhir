"""Matched experiment suite with an enforced, forwarded HTTP request budget.

All policy traffic, verifier controls, CAPTCHA requests, and Chromium page
resources pass through the local counting proxy. The proxy forwards at most
1,640 requests to Juice Shop per trial; excess attempts receive a local 429
and are reported separately. Outputs are isolated from the earlier runs.
"""
from __future__ import annotations

import csv
import http.client
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROJECT = ROOT / "rl_pentest"
JUICE_SHOP = ROOT / "juice-shop"
OUT_DIR = HERE / "runs_exact_1640"
AUDIT_JSON = HERE / "ground_truth_audit_independent_v2" / "independent_audit.json"
NODE = Path(r"C:\Users\Kevin Setiawan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe")
TARGET_PORT = 3001
PROXY_PORT = 3000
REQUEST_BUDGET = 1640
MAX_EPISODES = 5000
sys.path.insert(0, str(PROJECT))

import experiment_runner as prior  # noqa: E402
from agent.q_learning_agent import QLearningAgent  # noqa: E402
from analyzer.browser_verifier import BrowserVerifier  # noqa: E402
from analyzer.response_analyzer import ResponseAnalyzer  # noqa: E402
from config import (  # noqa: E402
    ALPHA, ENDPOINTS, EPSILON_DECAY, EPSILON_MIN, EPSILON_START, GAMMA,
    OPTIMISTIC_INIT, PAYLOADS_FILE, REQUEST_TIMEOUT, TOTAL_EPISODES, XSS_PAGES,
)
from engine.http_client import HTTPClient  # noqa: E402
from engine.payload_generator import PayloadGenerator  # noqa: E402
from reward.reward_system import RewardSystem  # noqa: E402
from training_loop import probe_endpoint_baselines, run_episode  # noqa: E402

prior.OUT_DIR = OUT_DIR
prior.BASE_URL = f"http://127.0.0.1:{PROXY_PORT}"


class RequestCounter:
    def __init__(self, limit: int):
        self.limit = limit
        self.forwarded = 0
        self.rejected = 0
        self.lock = threading.Lock()


class BudgetProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args):
        pass

    def _forward(self):
        counter: RequestCounter = self.server.counter  # type: ignore[attr-defined]
        with counter.lock:
            if counter.forwarded >= counter.limit:
                counter.rejected += 1
                blocked = True
            else:
                counter.forwarded += 1
                blocked = False
        if blocked:
            payload = b"Request budget reached; this request was not forwarded to Juice Shop."
            self.send_response(429)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else None
        headers = {
            key: value for key, value in self.headers.items()
            if key.lower() not in {"host", "connection", "content-length", "transfer-encoding"}
        }
        headers["Host"] = f"127.0.0.1:{TARGET_PORT}"
        connection = http.client.HTTPConnection("127.0.0.1", TARGET_PORT, timeout=45)
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            response_body = response.read()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in {"connection", "content-length", "transfer-encoding", "keep-alive"}:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(response_body)))
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD" and response_body:
                self.wfile.write(response_body)
        except Exception:
            try:
                self.send_error(502, "counted proxy could not reach Juice Shop")
            except OSError:
                pass
        finally:
            connection.close()

    do_GET = _forward
    do_POST = _forward
    do_PUT = _forward
    do_PATCH = _forward
    do_DELETE = _forward
    do_OPTIONS = _forward
    do_HEAD = _forward


class CountedProxy(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port: int, counter: RequestCounter):
        super().__init__(("127.0.0.1", port), BudgetProxyHandler)
        self.counter = counter


class JuiceShopProcess(prior.JuiceShopProcess):
    def start(self):
        log_dir = OUT_DIR / "server_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.stdout_handle = open(log_dir / f"{self.run_id}.stdout.log", "wb")
        self.stderr_handle = open(log_dir / f"{self.run_id}.stderr.log", "wb")
        env = os.environ.copy()
        env["PORT"] = str(TARGET_PORT)
        self.process = subprocess.Popen(
            [str(NODE), "build/app.js"], cwd=JUICE_SHOP, env=env,
            stdout=self.stdout_handle, stderr=self.stderr_handle,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"Juice Shop exited early; see server log for {self.run_id}")
            try:
                response = requests.get(f"http://127.0.0.1:{TARGET_PORT}/", timeout=3)
                if response.status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(1)
        raise TimeoutError(f"Juice Shop did not become ready for {self.run_id}")


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
            base_reward = self.vulnerability_reward if verified else self.anomaly_reward
        elif analysis.get("error_flag") or analysis.get("reflected_flag") or analysis.get("significant_change"):
            base_reward = self.anomaly_reward
        else:
            base_reward = self.normal_reward
        return base_reward + self._length_bonus(analysis)


def make_agent(mode: str, n_actions: int):
    if mode in {"ql", "ql_no_verify_reward", "ql_reward_low", "ql_reward_high"}:
        return QLearningAgent(
            n_actions=n_actions, alpha=ALPHA, gamma=GAMMA, epsilon=EPSILON_START,
            min_epsilon=EPSILON_MIN, decay=EPSILON_DECAY, qtable_file=None,
            optimistic_init=OPTIMISTIC_INIT,
        )
    if mode == "random":
        return prior.RandomPolicy(n_actions)
    if mode == "fixed":
        return prior.FixedOrderPolicy(n_actions)
    raise ValueError(f"Unknown mode: {mode}")


def make_reward_system(mode: str):
    if mode == "ql_reward_low":
        return RewardVariant(25, 5)
    if mode == "ql_reward_high":
        return RewardVariant(100, 20)
    return RewardSystem()


def run_trial(mode: str, seed: int, run_id: str, counter: RequestCounter, positive_actions: set[int]):
    import random

    random.seed(seed)
    np.random.seed(seed)
    generator = PayloadGenerator(PAYLOADS_FILE, n_endpoints=len(ENDPOINTS))
    n_actions = generator.get_action_count()
    agent = make_agent(mode, n_actions)
    analyzer = ResponseAnalyzer()
    client = HTTPClient(f"http://127.0.0.1:{PROXY_PORT}", endpoints=ENDPOINTS, timeout=REQUEST_TIMEOUT)
    browser = BrowserVerifier(f"http://127.0.0.1:{PROXY_PORT}")
    reward_system = make_reward_system(mode)
    baseline_probes = probe_endpoint_baselines(client, analyzer)
    requests_after_setup = counter.forwarded
    current_state = ("2xx", 1, 0, 0, 0, 0, 0, 0)
    discovered: set[int] = set()
    seen_actions: set[int] = set()
    verification_requests = 0
    total_reward = 0
    records = []
    first_discovery = None
    all_oracle_positives_episode = None
    started = time.monotonic()
    episode = 0

    while counter.forwarded < REQUEST_BUDGET and episode < MAX_EPISODES:
        episode += 1
        record, next_state, reward, verification_count = run_episode(
            agent, generator, client, analyzer, reward_system, current_state,
            mask=set(discovered), browser_verifier=browser, xss_pages=XSS_PAGES,
            verification_guided_reward=(mode != "ql_no_verify_reward"),
        )
        record["episode"] = episode
        records.append(record)
        current_state = next_state
        total_reward += reward
        verification_requests += verification_count
        seen_actions.add(record["action_index"])
        if record["verified"] and record["vulnerability"] != "none":
            discovered.add(record["action_index"])
            if first_discovery is None:
                first_discovery = episode
            if all_oracle_positives_episode is None and positive_actions.issubset(discovered):
                all_oracle_positives_episode = episode
        agent.decay_exploration()
        if episode % 500 == 0:
            print(f"{run_id}: primary action {episode}; forwarded HTTP {counter.forwarded}/{REQUEST_BUDGET}", flush=True)

    duration = round(time.monotonic() - started, 2)
    browser_navigations = browser.navigations
    browser_warning = None if browser.available else browser.unavailable_reason
    browser.close()
    client.session.close()

    tp = sorted(discovered & positive_actions)
    fp = sorted(discovered - positive_actions)
    fn = sorted(positive_actions - discovered)
    unique_locations = sorted({
        (row["endpoint_index"], row["vulnerability"])
        for row in records if row["verified"] and row["vulnerability"] != "none"
    })
    summary = {
        "run_id": run_id, "mode": mode, "seed": seed,
        "primary_episodes": episode, "action_count": n_actions,
        "verified_action_count": len(discovered), "verified_actions": sorted(discovered),
        "independent_oracle_positive_action_count": len(positive_actions),
        "oracle_true_positive_actions": tp, "oracle_false_positive_actions": fp,
        "oracle_missed_positive_actions": fn,
        "independent_oracle_full_coverage_episode": all_oracle_positives_episode,
        "first_verified_episode": first_discovery,
        "unique_actions_visited": len(seen_actions),
        "unique_endpoint_class_pairs": len(unique_locations),
        "endpoint_class_pairs": [list(item) for item in unique_locations],
        "setup_target_requests_before_primary_actions": requests_after_setup,
        "baseline_endpoint_count": len(baseline_probes),
        "total_requests_forwarded_to_target": counter.forwarded,
        "request_budget": REQUEST_BUDGET,
        "budget_exactly_used": counter.forwarded == REQUEST_BUDGET,
        "over_budget_requests_rejected_at_proxy": counter.rejected,
        "verification_requests_reported_by_agent": verification_requests,
        "browser_top_level_navigations": browser_navigations,
        "cumulative_reward": total_reward,
        "training_duration_seconds": duration,
        "epsilon_decay": EPSILON_DECAY if mode in {"ql", "ql_no_verify_reward", "ql_reward_low", "ql_reward_high"} else None,
        "verification_guided_reward": mode != "ql_no_verify_reward",
        "verification_still_used_for_reporting_and_action_masking": True,
        "browser_verifier_warning": browser_warning,
    }
    run_dir = OUT_DIR / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / f"{run_id}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (run_dir / f"{run_id}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps({k: summary[k] for k in (
        "run_id", "primary_episodes", "verified_action_count", "oracle_true_positive_actions",
        "oracle_false_positive_actions", "oracle_missed_positive_actions",
        "independent_oracle_full_coverage_episode", "unique_actions_visited",
        "total_requests_forwarded_to_target", "over_budget_requests_rejected_at_proxy",
        "training_duration_seconds"
    )}, ensure_ascii=False), flush=True)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    positive_actions = set(audit["positive_action_indices"])
    plan = prior.build_plan()
    print(json.dumps({
        "suite": "independent_oracle_exact_forwarded_request_budget_v1",
        "runs": len(plan), "seeds": prior.SEEDS,
        "request_budget_per_run": REQUEST_BUDGET,
        "oracle_positive_actions": sorted(positive_actions),
        "node_version": subprocess.check_output([str(NODE), "--version"], text=True).strip(),
        "juice_shop_version": "20.2.0", "juice_shop_port": TARGET_PORT,
        "counted_proxy_port": PROXY_PORT,
        "plan": plan,
    }, indent=2), flush=True)

    counter = RequestCounter(REQUEST_BUDGET)
    proxy = CountedProxy(PROXY_PORT, counter)
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()
    try:
        for index, (mode, seed) in enumerate(plan, start=1):
            run_id = f"{index:02d}_{mode}_seed{seed}"
            print(f"Starting {index}/{len(plan)}: {run_id}", flush=True)
            server = JuiceShopProcess(run_id)
            server.start()
            try:
                with counter.lock:
                    counter.forwarded = 0
                    counter.rejected = 0
                run_trial(mode, seed, run_id, counter, positive_actions)
                if counter.forwarded != REQUEST_BUDGET:
                    raise RuntimeError(f"{run_id} stopped at {counter.forwarded}, expected {REQUEST_BUDGET}")
            finally:
                server.stop()
    finally:
        proxy.shutdown()
        proxy.server_close()
        proxy_thread.join(timeout=5)

    print("EXACT REQUEST BUDGET EXPERIMENT SUITE COMPLETE", flush=True)


if __name__ == "__main__":
    main()
