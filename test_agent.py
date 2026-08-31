import json
import os
import sys
import tempfile
import unittest

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rl_pentest"))

from agent.dqn_agent import DQNAgent, ReplayBuffer, encode_state
from agent.q_learning_agent import QLearningAgent
from analyzer.response_analyzer import ResponseAnalyzer
from reward.reward_system import RewardSystem
from engine.payload_generator import PayloadGenerator
from config import (
    ALPHA,
    GAMMA,
    EPSILON_START,
    EPSILON_MIN,
    OPTIMISTIC_INIT,
    REWARD_VULNERABILITY,
    REWARD_ANOMALY,
    REWARD_NONE,
    REWARD_REQUEST_ERROR,
)


class TestQLearningAgent(unittest.TestCase):
    def setUp(self):
        self.agent = QLearningAgent(n_actions=10)

    def test_initial_hyperparameters(self):
        self.assertEqual(self.agent.alpha, ALPHA)
        self.assertEqual(self.agent.gamma, GAMMA)
        self.assertEqual(self.agent.epsilon, EPSILON_START)
        self.assertEqual(self.agent.min_epsilon, EPSILON_MIN)
        self.assertEqual(self.agent.decay, 0.90)
        self.assertEqual(self.agent.optimistic_init, OPTIMISTIC_INIT)

    def test_choose_action_returns_valid_index(self):
        state = ("2xx", "medium", 0, 0)
        for _ in range(100):
            action = self.agent.choose_action(state)
            self.assertGreaterEqual(action, 0)
            self.assertLess(action, 10)

    def test_learn_updates_q_table(self):
        state = ("2xx", "small", 0, 0)
        next_state = ("4xx", "small", 1, 0)
        self.agent.learn(state, 3, 50, next_state)
        state_key = self.agent._state_key(state)
        self.assertIn(state_key, self.agent.qtable)

    def test_decay_exploration(self):
        initial = self.agent.epsilon
        self.agent.decay_exploration()
        self.assertLess(self.agent.epsilon, initial)
        self.assertGreaterEqual(self.agent.epsilon, EPSILON_MIN)

    def test_epsilon_never_below_min(self):
        self.agent.epsilon = EPSILON_MIN
        self.agent.decay_exploration()
        self.assertEqual(self.agent.epsilon, EPSILON_MIN)

    def test_save_and_load_qtable(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        try:
            from pathlib import Path
            self.agent.qtable = {"2xx|small|0|0": [1.0, 2.0, 3.0]}
            self.agent.qtable_file = Path(tmp)
            self.agent.save_qtable()
            self.assertTrue(os.path.exists(tmp))

            loaded = QLearningAgent(n_actions=10, qtable_file=tmp)
            self.assertIn("2xx|small|0|0", loaded.qtable)
            self.assertEqual(loaded.qtable["2xx|small|0|0"][1], 2.0)
        finally:
            os.unlink(tmp)

    def test_get_best_action_values(self):
        state = ("5xx", "large", 1, 1)
        values = self.agent.get_best_action_values(state)
        self.assertEqual(len(values), 10)


class TestRewardSystem(unittest.TestCase):
    def setUp(self):
        self.rs = RewardSystem()

    def test_vulnerability_reward(self):
        analysis = {"vulnerability": "sqli", "request_error": False}
        self.assertEqual(self.rs.compute_reward(analysis), REWARD_VULNERABILITY)

    def test_xss_reward(self):
        analysis = {"vulnerability": "xss", "request_error": False}
        self.assertEqual(self.rs.compute_reward(analysis), REWARD_VULNERABILITY)

    def test_fuzzing_reward(self):
        analysis = {"vulnerability": "fuzzing", "request_error": False}
        self.assertEqual(self.rs.compute_reward(analysis), REWARD_VULNERABILITY)

    def test_error_anomaly_reward(self):
        analysis = {"vulnerability": "none", "error_flag": True, "reflected_flag": False, "significant_change": False, "request_error": False}
        self.assertEqual(self.rs.compute_reward(analysis), REWARD_ANOMALY)

    def test_reflection_anomaly_reward(self):
        analysis = {"vulnerability": "none", "error_flag": False, "reflected_flag": True, "significant_change": False, "request_error": False}
        self.assertEqual(self.rs.compute_reward(analysis), REWARD_ANOMALY)

    def test_significant_change_anomaly_reward(self):
        analysis = {"vulnerability": "none", "error_flag": False, "reflected_flag": False, "significant_change": True, "request_error": False}
        self.assertEqual(self.rs.compute_reward(analysis), REWARD_ANOMALY)

    def test_normal_reward(self):
        analysis = {"vulnerability": "none", "error_flag": False, "reflected_flag": False, "significant_change": False, "request_error": False}
        self.assertEqual(self.rs.compute_reward(analysis), REWARD_NONE)

    def test_request_error_reward(self):
        analysis = {"request_error": True}
        self.assertEqual(self.rs.compute_reward(analysis), REWARD_REQUEST_ERROR)


class TestPayloadGenerator(unittest.TestCase):
    def setUp(self):
        payloads_file = os.path.join(os.path.dirname(__file__), "rl_pentest", "data", "payloads.json")
        self.pg = PayloadGenerator(payloads_file)

    def test_payload_count(self):
        self.assertGreater(self.pg.get_action_count(), 0)

    def test_get_payload_returns_dict(self):
        payload = self.pg.get_payload(0)
        self.assertIn("name", payload)
        self.assertIn("payload", payload)
        self.assertIn("category", payload)

    def test_get_payload_out_of_range(self):
        count = self.pg.get_action_count()
        with self.assertRaises(IndexError):
            self.pg.get_payload(count)

    def test_get_payload_text(self):
        text = self.pg.get_payload_text(0)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)

    def test_get_action_name(self):
        name = self.pg.get_action_name(0)
        self.assertIsInstance(name, str)

    def test_action_count_with_endpoints(self):
        payloads_file = os.path.join(os.path.dirname(__file__), "rl_pentest", "data", "payloads.json")
        pg = PayloadGenerator(payloads_file, n_endpoints=8)
        self.assertEqual(pg.get_action_count(), pg.n_payloads * 8)
        payload, endpoint = pg.get_payload_and_endpoint(pg.n_payloads * 7 + 1)
        self.assertEqual(endpoint, 7)
        self.assertEqual(payload["name"], pg.payloads[1]["name"])

    def test_list_payloads(self):
        payloads = self.pg.list_payloads()
        self.assertIsInstance(payloads, list)


class MockResponse:
    def __init__(self, text: str, status_code: int, headers: dict = None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}


class TestResponseAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = ResponseAnalyzer(baseline_length=100, variance_threshold=0.15)

    def test_sqli_detected_via_error(self):
        resp = MockResponse("syntax error at line 1", 500)
        result = self.analyzer.analyze(resp, "' OR '1'='1")
        self.assertEqual(result["vulnerability"], "sqli")
        self.assertEqual(result["status_category"], "5xx")
        self.assertTrue(result["error_flag"])

    def test_sqli_detected_via_significant_change(self):
        resp = MockResponse("A" * 200, 200)
        result = self.analyzer.analyze(resp, "' UNION SELECT NULL--")
        self.assertEqual(result["vulnerability"], "sqli")

    def test_xss_detected(self):
        resp = MockResponse("<script>alert('test')</script>reflected", 200)
        result = self.analyzer.analyze(resp, "<script>alert('test')</script>")
        self.assertEqual(result["vulnerability"], "xss")
        self.assertTrue(result["reflected_flag"])

    def test_normal_request_no_vuln(self):
        resp = MockResponse("A" * 105, 200)
        result = self.analyzer.analyze(resp, "normal")
        self.assertEqual(result["vulnerability"], "none")
        self.assertFalse(result["error_flag"])
        self.assertFalse(result["reflected_flag"])
        self.assertFalse(result["significant_change"])
        self.assertFalse(result["request_error"])

    def test_error_status_category(self):
        resp = MockResponse("", 403)
        result = self.analyzer.analyze(resp, "test")
        self.assertEqual(result["status_category"], "4xx")

    def test_reflected_flag(self):
        resp = MockResponse("payload_abc_here", 200)
        result = self.analyzer.analyze(resp, "payload_abc_here")
        self.assertTrue(result["reflected_flag"])

    def test_none_response_returns_error(self):
        result = self.analyzer.analyze(None, "test")
        self.assertTrue(result["request_error"])
        self.assertEqual(result["vulnerability"], "none")

    def test_significant_change_detection(self):
        resp = MockResponse("A" * 200, 200)
        result = self.analyzer.analyze(resp, "test")
        self.assertTrue(result["significant_change"])

    def test_baseline_length_boundary(self):
        resp = MockResponse("A" * 115, 200)
        result = self.analyzer.analyze(resp, "test")
        self.assertTrue(result["significant_change"])
        resp2 = MockResponse("A" * 114, 200)
        result2 = self.analyzer.analyze(resp2, "test")
        self.assertFalse(result2["significant_change"])

    def test_categorize_length_cat0(self):
        self.assertEqual(ResponseAnalyzer.categorize_length(0), 0)
        self.assertEqual(ResponseAnalyzer.categorize_length(1499), 0)

    def test_categorize_length_cat1(self):
        self.assertEqual(ResponseAnalyzer.categorize_length(1500), 1)
        self.assertEqual(ResponseAnalyzer.categorize_length(2499), 1)

    def test_categorize_length_cat2(self):
        self.assertEqual(ResponseAnalyzer.categorize_length(2500), 2)
        self.assertEqual(ResponseAnalyzer.categorize_length(3499), 2)

    def test_categorize_length_cat3(self):
        self.assertEqual(ResponseAnalyzer.categorize_length(3500), 3)
        self.assertEqual(ResponseAnalyzer.categorize_length(9999), 3)

    def test_analysis_includes_length_category(self):
        resp = MockResponse("A" * 200, 200)
        result = self.analyzer.analyze(resp, "test")
        self.assertIn("length_category", result)

    def test_reward_with_length_bonus_high(self):
        analysis = {"vulnerability": "sqli", "request_error": False, "error_flag": True,
                     "reflected_flag": False, "significant_change": True, "length_category": 3}
        reward = RewardSystem().compute_reward(analysis)
        self.assertEqual(reward, 60)

    def test_reward_with_length_bonus_normal(self):
        analysis = {"vulnerability": "none", "request_error": False, "error_flag": False,
                     "reflected_flag": False, "significant_change": False, "length_category": 2}
        reward = RewardSystem().compute_reward(analysis)
        self.assertEqual(reward, 4)

    def test_reward_error_no_bonus(self):
        analysis = {"request_error": True, "length_category": 3}
        reward = RewardSystem().compute_reward(analysis)
        self.assertEqual(reward, -5)

    def test_xss_detected_via_script_tag(self):
        resp = MockResponse('{"reviews":[{"message":"<script>alert(1)</script>"}]}', 200, {"Content-Type": "application/json"})
        result = self.analyzer.analyze(resp, "<script>alert('test')</script>")
        self.assertEqual(result["vulnerability"], "xss")

    def test_fuzzing_detected_via_500(self):
        resp = MockResponse("Internal Server Error", 500)
        result = self.analyzer.analyze(resp, "%s%s%s%s%s")
        self.assertEqual(result["vulnerability"], "fuzzing")

    def test_fuzzing_detected_via_error(self):
        resp = MockResponse("error in format string", 500, {"Content-Type": "text/html"})
        result = self.analyzer.analyze(resp, "%s%s%s%s%s")
        self.assertEqual(result["vulnerability"], "fuzzing")

    def test_response_time_category_fast(self):
        self.assertEqual(ResponseAnalyzer.categorize_response_time(0.1), 0)

    def test_response_time_category_medium(self):
        self.assertEqual(ResponseAnalyzer.categorize_response_time(0.5), 1)

    def test_response_time_category_slow(self):
        self.assertEqual(ResponseAnalyzer.categorize_response_time(3.0), 2)

    def test_content_type_category_json(self):
        resp = MockResponse("{}", 200, {"Content-Type": "application/json"})
        result = self.analyzer.analyze(resp, "test")
        self.assertEqual(result["content_type_category"], 0)

    def test_content_type_category_html(self):
        resp = MockResponse("<html></html>", 200, {"Content-Type": "text/html"})
        result = self.analyzer.analyze(resp, "test")
        self.assertEqual(result["content_type_category"], 1)

    def test_analysis_includes_new_fields(self):
        resp = MockResponse("hello", 200, {"Content-Type": "text/plain"})
        result = self.analyzer.analyze(resp, "test", response_time=1.0)
        self.assertIn("response_time_category", result)
        self.assertIn("content_type_category", result)
        self.assertIn("has_csp", result)

    def test_significant_change_uses_endpoint_baseline(self):
        analyzer = ResponseAnalyzer(baseline_length=100, variance_threshold=0.15)
        analyzer.set_baselines({5: 1000})
        resp = MockResponse("A" * 1100, 200)
        result = analyzer.analyze(resp, "test", endpoint_index=5)
        self.assertFalse(result["significant_change"])
        resp2 = MockResponse("A" * 400, 200)
        result2 = analyzer.analyze(resp2, "test", endpoint_index=5)
        self.assertTrue(result2["significant_change"])

    def test_significant_change_fallback_to_default_baseline(self):
        analyzer = ResponseAnalyzer(baseline_length=100, variance_threshold=0.15)
        resp = MockResponse("A" * 50, 200)
        result = analyzer.analyze(resp, "test", endpoint_index=5)
        self.assertTrue(result["significant_change"])

    def test_reward_verified_vuln(self):
        analysis = {"vulnerability": "sqli", "request_error": False, "error_flag": True,
                     "reflected_flag": False, "significant_change": True, "length_category": 1}
        reward = RewardSystem().compute_reward(analysis, verified=True)
        self.assertEqual(reward, 50)

    def test_reward_unverified_vuln(self):
        analysis = {"vulnerability": "sqli", "request_error": False, "error_flag": True,
                     "reflected_flag": False, "significant_change": True, "length_category": 1}
        reward = RewardSystem().compute_reward(analysis, verified=False)
        self.assertEqual(reward, 10)


STATE_8 = ("2xx", 1, 0, 0, 0, 3, 1, 1)


class TestDQNAgent(unittest.TestCase):
    def setUp(self):
        self.agent = DQNAgent(n_actions=88, hidden_dim=16, batch_size=8)

    def test_encode_state_dimension(self):
        vec = encode_state(STATE_8)
        self.assertEqual(len(vec), 28)
        self.assertEqual(vec[0], 1.0)
        self.assertEqual(vec[5:9].tolist(), [0.0, 1.0, 0.0, 0.0])
        self.assertEqual(vec[15], 1.0)
        self.assertEqual(vec[-5:].tolist(), [0.0, 1.0, 0.0, 0.0, 0.0])

    def test_choose_action_within_bounds(self):
        for _ in range(50):
            self.assertGreaterEqual(self.agent.choose_action(STATE_8), 0)
            self.assertLess(self.agent.choose_action(STATE_8), 88)

    def test_replay_buffer_push_and_sample(self):
        buffer = ReplayBuffer(capacity=8)
        for _ in range(8):
            buffer.push(STATE_8, 1, 10.0, STATE_8, False)
        states, actions, rewards, next_states, dones = buffer.sample(8)
        self.assertEqual(states.shape[1], 28)
        self.assertEqual(len(actions), 8)
        self.assertEqual(actions.shape, (8, 1))
        self.assertEqual(rewards.shape, (8, 1))

    def test_learn_updates_policy(self):
        before = [float(self.agent.policy_net(torch.FloatTensor(encode_state(STATE_8)).unsqueeze(0))[0][0].item())]
        for _ in range(20):
            self.agent.learn(STATE_8, 3, 50.0, STATE_8)
        self.agent.target_net.load_state_dict(self.agent.policy_net.state_dict())
        after = [float(self.agent.policy_net(torch.FloatTensor(encode_state(STATE_8)).unsqueeze(0))[0][0].item())]
        self.assertNotEqual(round(before[0], 8), round(after[0], 8))

    def test_decay_epsilon(self):
        before = self.agent.epsilon
        self.agent.decay_exploration()
        self.assertLess(self.agent.epsilon, before)
        self.assertGreaterEqual(self.agent.epsilon, self.agent.min_epsilon)

    def test_save_and_load_model(self):
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            tmp = f.name
        try:
            self.agent.save_model(tmp)
            self.assertTrue(os.path.exists(tmp))
            loaded = DQNAgent(n_actions=88, hidden_dim=16, batch_size=8)
            self.assertTrue(loaded.load_model(tmp))
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
