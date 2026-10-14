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
from analyzer.browser_verifier import BrowserVerifier, instrument
from analyzer.response_analyzer import ResponseAnalyzer
from reward.reward_system import RewardSystem
from engine.payload_generator import PayloadGenerator
from evaluation.metrics import compute_metrics
from config import (
    ALPHA,
    ENDPOINTS,
    GAMMA,
    EPSILON_START,
    EPSILON_MIN,
    OPTIMISTIC_INIT,
    PAYLOADS_FILE,
    REWARD_VULNERABILITY,
    REWARD_ANOMALY,
    REWARD_NONE,
    REWARD_REQUEST_ERROR,
    XSS_PAGES,
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

    def test_sqli_not_flagged_on_2xx_without_significant_change(self):
        resp = MockResponse("A" * 105, 200)
        result = self.analyzer.analyze(resp, "' UNION SELECT NULL--")
        self.assertEqual(result["vulnerability"], "none")

    def test_sqli_tautology_reflected_into_2xx(self):
        text = "' OR '1'='1" + " A" * 200
        resp = MockResponse(text, 200)
        result = self.analyzer.analyze(resp, "' OR '1'='1")
        self.assertEqual(result["vulnerability"], "sqli")

    def test_sqli_db_error_on_4xx(self):
        resp = MockResponse("SequelizeDatabaseError: SQLITE_ERROR: syntax error", 500)
        result = self.analyzer.analyze(resp, "' UNION SELECT NULL--")
        self.assertEqual(result["vulnerability"], "sqli")

    def test_sqli_generic_500_not_detected(self):
        resp = MockResponse("Internal Server Error", 500)
        result = self.analyzer.analyze(resp, "' OR '1'='1")
        self.assertEqual(result["vulnerability"], "none")

    def test_5xx_xss_not_detected(self):
        resp = MockResponse("Internal Server Error", 500)
        result = self.analyzer.analyze(resp, "<script>alert('test')</script>")
        self.assertEqual(result["vulnerability"], "none")

    def test_ftp_listing_not_detected(self):
        resp = MockResponse("Index of /ftp/ - OWASP Juice Shop", 200)
        result = self.analyzer.analyze(resp, "../../../etc/passwd")
        self.assertEqual(result["vulnerability"], "none")

    def test_xss_detected(self):
        resp = MockResponse("<script>alert('test')</script>reflected", 200, {"Content-Type": "text/html"})
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

    def test_xss_not_detected_in_json_reflection(self):
        # Refleksi di dalam JSON tidak pernah dieksekusi browser, jadi bukan
        # bukti XSS. Inilah yang dulu membuat /rest/track-order reported FALSE POSITIVE.
        resp = MockResponse('{"status":"success","data":[{"orderId":"<img src=x onerror=alert(1)>"}]}',
                            200, {"Content-Type": "application/json"})
        result = self.analyzer.analyze(resp, "<img src=x onerror=alert(1)>")
        self.assertEqual(result["vulnerability"], "none")
        self.assertTrue(result["reflected_flag"])

    def test_xss_not_detected_in_plain_text(self):
        resp = MockResponse("No order found: <img src=x onerror=alert(1)>", 200,
                            {"Content-Type": "text/plain"})
        result = self.analyzer.analyze(resp, "<img src=x onerror=alert(1)>")
        self.assertEqual(result["vulnerability"], "none")

    def test_served_as_html_helper(self):
        self.assertTrue(ResponseAnalyzer.served_as_html(
            MockResponse("", 200, {"Content-Type": "text/html; charset=utf-8"})))
        self.assertTrue(ResponseAnalyzer.served_as_html(
            MockResponse("", 200, {"Content-Type": "application/xhtml+xml"})))
        self.assertFalse(ResponseAnalyzer.served_as_html(
            MockResponse("", 200, {"Content-Type": "application/json"})))
        self.assertFalse(ResponseAnalyzer.served_as_html(None))

    def test_sqli_detected_via_like_wildcard(self):
        # '%s%s%s%s' membatalkan filter LIKE sehingga membocorkan seluruh baris.
        resp = MockResponse("A" * 300, 200, {"Content-Type": "application/json"})
        result = self.analyzer.analyze(resp, "%s%s%s%s%s%s%s%s")
        self.assertEqual(result["vulnerability"], "sqli")

    def test_file_disclosure_via_poison_null_byte(self):
        # Isi package.json yang bocor lewat pemotongan %2500 pada /ftp/.
        resp = MockResponse('{\r\n  "name": "juice-shop",\r\n  "version": "6.2.0",\r\n  "dependencies": {',
                            200, {"Content-Type": "application/octet-stream"})
        result = self.analyzer.analyze(resp, "package.json.bak%2500.md", surface="file")
        self.assertEqual(result["vulnerability"], "fuzzing")

    def test_file_disclosure_via_coupon_content(self):
        resp = MockResponse("n<MibgC7sn\nmNYS#gC7sn\no*IVigC7sn", 200,
                            {"Content-Type": "application/octet-stream"})
        result = self.analyzer.analyze(resp, "coupons_2013.md.bak%2500.md", surface="file")
        self.assertEqual(result["vulnerability"], "fuzzing")

    def test_public_markdown_listing_not_disclosure(self):
        # acquisitions.md memang disajikan publik oleh /ftp/, bukan kebocoran.
        resp = MockResponse("# Planned Acquisitions\n\nThis document is confidential", 200,
                            {"Content-Type": "text/markdown"})
        result = self.analyzer.analyze(resp, "acquisitions.md", surface="file")
        self.assertEqual(result["vulnerability"], "none")

    def test_extension_filter_bypass_detected_by_content_type_mismatch(self):
        # Diminta .pdf, tetapi server menyajikan YAML karena pemotongan %2500.
        resp = MockResponse("title: Suspicious error messages\ndescription: Detects errors",
                            200, {"Content-Type": "text/yaml"})
        result = self.analyzer.analyze(resp, "suspicious_errors.yml%2500.pdf", surface="file")
        self.assertEqual(result["vulnerability"], "fuzzing")

    def test_extension_filter_bypass_not_flagged_when_type_matches(self):
        resp = MockResponse("# Planned Acquisitions", 200, {"Content-Type": "text/markdown"})
        result = self.analyzer.analyze(resp, "acquisitions.md%2500.md", surface="file")
        self.assertEqual(result["vulnerability"], "none")

    def test_extension_filter_bypass_ignored_on_error_status(self):
        resp = MockResponse("Error: Only .md and .pdf files are allowed!", 403,
                            {"Content-Type": "text/html"})
        result = self.analyzer.analyze(resp, "package.json%2500.md", surface="file")
        self.assertEqual(result["vulnerability"], "none")

    def test_file_rules_do_not_fire_on_non_file_surface(self):
        # Endpoint non-berkas tidak boleh dilaporkan kebocoran berkas hanya
        # karena tipe kontennya bukan markdown/pdf.
        resp = MockResponse('{"name":"juice-shop"}', 200, {"Content-Type": "application/json"})
        result = self.analyzer.analyze(resp, "package.json.bak%2500.md", surface="plain")
        self.assertEqual(result["vulnerability"], "none")

    def test_sqli_rules_do_not_fire_on_non_sql_surface(self):
        # /api/Challenges juga membocorkan seluruh koleksi saat diberi wildcard,
        # tetapi backend-nya NoSQL sehingga itu bukan SQL Injection.
        resp = MockResponse("A" * 300, 200, {"Content-Type": "application/json"})
        self.assertEqual(
            self.analyzer.analyze(resp, "%s%s%s%s%s%s%s%s", surface="plain")["vulnerability"],
            "none")
        self.assertEqual(
            self.analyzer.analyze(resp, "%s%s%s%s%s%s%s%s", surface="sql")["vulnerability"],
            "sqli")

    def test_fuzzing_detected_via_disclosure(self):
        resp = MockResponse("root:x:0:0:root:/root:/bin/bash", 200)
        result = self.analyzer.analyze(resp, "../../../etc/passwd", surface="file")
        self.assertEqual(result["vulnerability"], "fuzzing")

    def test_fuzzing_5xx_echoing_raw_probe(self):
        resp = MockResponse("error at %s%s%s%s%s position", 500, {"Content-Type": "text/html"})
        result = self.analyzer.analyze(resp, "%s%s%s%s%s")
        self.assertEqual(result["vulnerability"], "fuzzing")

    def test_fuzzing_generic_500_not_detected(self):
        resp = MockResponse("Internal Server Error", 500)
        result = self.analyzer.analyze(resp, "%s%s%s%s%s")
        self.assertEqual(result["vulnerability"], "none")

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


class FakeClient:
    def __init__(self, responses, surface="sql"):
        self.responses = list(responses)
        self.calls = 0
        self.surface = surface

    def surface_of(self, endpoint_index):
        return self.surface

    def send_payload(self, payload, endpoint_index=None):
        self.calls += 1
        if not self.responses:
            raise RuntimeError("no more responses")
        return self.responses.pop(0)


class TestVerifyVulnerability(unittest.TestCase):
    def setUp(self):
        self.analyzer = ResponseAnalyzer(baseline_length=100, variance_threshold=0.15)

    def test_verified_when_controls_clean(self):
        client = FakeClient([
            MockResponse("no result", 200),
            MockResponse("A" * 100, 200),
        ])
        from training_loop import verify_vulnerability
        verified, controls = verify_vulnerability(client, self.analyzer, "' OR '1'='1", 0, "sqli")
        self.assertTrue(verified)
        self.assertEqual(controls, 2)
        self.assertEqual(client.calls, 2)

    def test_ineffective_mutant_is_skipped_as_control(self):
        # Wildcard '%s%s%s%s' tidak memuat kutip untuk dinetralkan, sehingga
        # mutannya identik dengan payload. Bila tetap dipakai sebagai kontrol,
        # ia akan selalu mereproduksi kelas yang sama dan menolak setiap temuan.
        client = FakeClient([MockResponse("no result", 200)])
        from training_loop import verify_vulnerability
        verified, controls = verify_vulnerability(client, self.analyzer, "%s%s%s%s%s", 0, "sqli")
        self.assertTrue(verified)
        self.assertEqual(controls, 1)
        self.assertEqual(client.calls, 1)

    def test_rejected_when_benign_reproduces_class(self):
        client = FakeClient([
            MockResponse("syntax error at line 1", 500),
        ])
        from training_loop import verify_vulnerability
        verified, _ = verify_vulnerability(client, self.analyzer, "' OR '1'='1", 0, "sqli")
        self.assertFalse(verified)

    def test_rejected_when_mutant_reproduces_class(self):
        client = FakeClient([
            MockResponse("ok", 200),
            MockResponse("syntax error at line 1", 500),
        ])
        from training_loop import verify_vulnerability
        verified, _ = verify_vulnerability(client, self.analyzer, "' OR '1'='1", 0, "sqli")
        self.assertFalse(verified)

    def test_rejected_on_connection_error(self):
        client = FakeClient([])
        from training_loop import verify_vulnerability
        verified, _ = verify_vulnerability(client, self.analyzer, "' OR '1'='1", 0, "sqli")
        self.assertFalse(verified)

    def test_neutralize_sqli_breaks_injection_out(self):
        from training_loop import neutralize_payload
        out = neutralize_payload("' OR '1'='1", "sqli")
        self.assertNotIn("'", out)
        out2 = neutralize_payload("' OR SLEEP(5)--", "sqli")
        self.assertNotIn("'", out2)
        self.assertNotIn("--", out2)
        self.assertNotIn("SLEEP(5)", out2)

    def test_neutralize_xss_strips_vectors(self):
        from training_loop import neutralize_payload
        out = neutralize_payload("<script>alert(document.domain)</script>", "xss")
        self.assertNotIn("<script", out)
        self.assertNotIn("alert(", out)


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


class TestBrowserVerifierInstrumentation(unittest.TestCase):
    """Instrumentasi harus mempertahankan bentuk vektor (tag + event) sehingga
    hanya mengganti isi handler; bila bentuk berubah, bukti eksekusi jadi tidak
    sahih karena tidak lagi merepresentasikan vektor asli."""

    def test_event_attribute_quoted(self):
        out = instrument('<img src=x onerror="alert(1)">')
        self.assertIn("onerror", out)
        self.assertIn("__RLP_XSS_CANARY__", out)
        self.assertNotIn("alert(1)", out)

    def test_event_attribute_bare(self):
        out = instrument("<img src=x onerror=alert(document.domain)>")
        self.assertIn("onerror", out)
        self.assertIn("__RLP_XSS_CANARY__", out)
        self.assertNotIn("alert(", out)

    def test_script_tag_body_replaced(self):
        out = instrument("<script>alert(document.domain)</script>")
        self.assertIn("__RLP_XSS_CANARY__", out)
        self.assertNotIn("alert(document.domain)", out)
        self.assertTrue(out.lower().startswith("<script"))
        self.assertTrue(out.lower().endswith("</script>"))

    def test_svg_onload(self):
        out = instrument("<svg onload=alert(1)>")
        self.assertIn("onload", out)
        self.assertNotIn("alert(1)", out)

    def test_javascript_uri(self):
        out = instrument("javascript:alert(1)")
        self.assertTrue(out.lower().startswith("javascript:"))
        self.assertNotIn("alert(1)", out)

    def test_unrecognized_vector_returns_none(self):
        self.assertIsNone(instrument("' OR '1'='1"))
        self.assertIsNone(instrument(""))

    def test_build_url_encodes_payload(self):
        verifier = BrowserVerifier("http://localhost:3000")
        url = verifier.build_url("/#/search?q={payload}", "<img src=x onerror=alert(1)>")
        self.assertTrue(url.startswith("http://localhost:3000/#/search?q="))
        self.assertNotIn(" ", url)
        self.assertIn("%3Cimg", url)

    def test_verifier_without_browser_returns_false(self):
        # Bila chromium tidak tersedia, verifier harus menolak (bukan menerima
        # temuan tanpa bukti) dan melapor alasannya.
        verifier = BrowserVerifier("http://localhost:3000")
        verifier.available = False
        self.assertFalse(verifier.verify("/#/search?q={payload}", "<img src=x onerror=alert(1)>"))


class TestXssSurfaceConfig(unittest.TestCase):
    def test_xss_pages_reference_existing_endpoints(self):
        for index in XSS_PAGES:
            self.assertLess(index, len(ENDPOINTS), f"endpoint_index {index} di luar daftar")
            self.assertIn("{payload}", XSS_PAGES[index])

    def test_xss_pages_use_hash_routes(self):
        for page in XSS_PAGES.values():
            self.assertTrue(page.startswith("/#/"), page)

    def test_action_space_is_endpoints_times_payloads(self):
        generator = PayloadGenerator(PAYLOADS_FILE, n_endpoints=len(ENDPOINTS))
        self.assertEqual(generator.get_action_count(), len(ENDPOINTS) * generator.n_payloads)

    def test_every_payload_has_known_category(self):
        with open(PAYLOADS_FILE, "r", encoding="utf-8") as handle:
            payloads = json.load(handle)
        for entry in payloads:
            self.assertIn(entry["category"], {"sqli", "xss", "fuzzing"}, entry["name"])
            self.assertTrue(entry["payload"])


class TestMetricsAccuracy(unittest.TestCase):
    def _row(self, **kwargs):
        base = {
            "reward": 0, "vulnerability": "none", "verified": True, "endpoint_index": 0,
            "response_time": 0.1, "rejected_candidate": "none", "browser_checked": False,
        }
        base.update(kwargs)
        return base

    def test_rejected_candidates_tracked(self):
        rows = [
            self._row(vulnerability="sqli", verified=True),
            self._row(rejected_candidate="fuzzing"),
            self._row(rejected_candidate="xss"),
        ]
        result = compute_metrics(rows)
        self.assertEqual(result["total_vulnerabilities"], 1)
        self.assertEqual(result["rejected_candidates"], 2)

    def test_detection_accuracy_is_not_reported(self):
        # Rasio vuln/(vuln+rejected) selalu 1.0 saat tidak ada yang ditolak,
        # sehingga menyesatkan. Dihapus demi metrik benchmark yang tidak circular.
        rows = [self._row(vulnerability="sqli", verified=True)]
        self.assertNotIn("detection_accuracy", compute_metrics(rows))

    def test_metrics_labelled_in_sample(self):
        self.assertIn("in-sample", compute_metrics([self._row()])["metrics_scope"])

    def test_browser_checked_counted(self):
        rows = [self._row(browser_checked=True), self._row(browser_checked=False)]
        self.assertEqual(compute_metrics(rows)["browser_checked_episodes"], 1)

    def test_vuln_hit_rate_is_per_request_not_ml_precision(self):
        rows = [
            self._row(vulnerability="sqli", verified=True),
            self._row(),
            self._row(),
            self._row(),
        ]
        result = compute_metrics(rows)
        self.assertEqual(result["vuln_hit_rate"], 0.25)
        self.assertNotIn("precision", result)

    def test_unique_locations_counted_per_endpoint_and_class(self):
        rows = [
            self._row(vulnerability="sqli", endpoint_index=0),
            self._row(vulnerability="sqli", endpoint_index=0),
            self._row(vulnerability="sqli", endpoint_index=4),
        ]
        result = compute_metrics(rows)
        self.assertEqual(result["total_vulnerabilities"], 3)
        self.assertEqual(result["unique_vuln_locations"], 2)

    def test_unverified_finding_is_not_counted_as_vulnerability(self):
        # Kolom verified harus bernilai False pada episode tanpa temuan, bukan
        # True untuk seluruh baris. Bila tidak, setiap request normal terhitung
        # sebagai temuan terverifikasi.
        rows = [self._row(verified=False), self._row(vulnerability="sqli", verified=False)]
        result = compute_metrics(rows)
        self.assertEqual(result["total_vulnerabilities"], 0)
        self.assertEqual(result["unique_vuln_locations"], 0)
        self.assertIsNone(result["time_to_first_vulnerability"])


class TestRunEpisodeVerificationFlag(unittest.TestCase):
    """Kolom 'verified' pada log harus bernilai True HANYA untuk temuan yang
    lolos kontrol-diferensial atau eksekusi browser, dan False untuk request
    biasa maupun kandidat yang ditolak."""

    def setUp(self):
        self.analyzer = ResponseAnalyzer()
        self.generator = PayloadGenerator(PAYLOADS_FILE, n_endpoints=len(ENDPOINTS))
        self.n_actions = self.generator.get_action_count()

    def _run(self, response, action):
        agent = QLearningAgent(n_actions=self.n_actions)
        agent.choose_action = lambda state, mask=None: action
        client = FakeClient([response, response, response, response, response])
        from training_loop import run_episode
        record, _next_state, _reward, _verification = run_episode(
            agent, self.generator, client, self.analyzer, RewardSystem(),
            current_state=("2xx", 1, 0, 0, 0, 0, 0, 0),
        )
        return record

    def _first_action(self, category, endpoint_index=0):
        for i in range(self.n_actions):
            payload, endpoint = self.generator.get_payload_and_endpoint(i)
            if payload.get("category") == category and endpoint == endpoint_index:
                return i
        self.fail(f"tidak ada payload kategori {category} di ep{endpoint_index}")

    def test_clean_response_is_not_marked_verified(self):
        # Respons netral pada endpoint non-serang tidak boleh jadi temuan.
        action = self._first_action("fuzzing", endpoint_index=7)
        result = self._run(MockResponse("nothing to see", 200), action=action)
        self.assertEqual(result["vulnerability"], "none")
        self.assertFalse(result["verified"])
        self.assertEqual(result["rejected_candidate"], "none")

    def test_rejected_candidate_is_not_verified(self):
        # Kontrol 'hello' direproduksi sebagai error SQL -> kandidat ditolak.
        analyzer = ResponseAnalyzer()
        original_analyze = analyzer.analyze
        sql_action = self._first_action("sqli", endpoint_index=0)
        agent = QLearningAgent(n_actions=self.n_actions)
        agent.choose_action = lambda state, mask=None: sql_action
        client = FakeClient([
            MockResponse("syntax error at line 1", 500),  # payload
            MockResponse("syntax error at line 1", 500),  # kontrol benign
        ])

        def analyze(response, payload, **kwargs):
            # Paksa kandidat SQLi agar jalur verifikasi pasti dieksekusi.
            # Method asli harus disimpan terpisah: analyze() memanggil
            # analyzer.analyze, sehingga memanggilnya lewat instance yang sudah
            # diganti akan ber rekursi tanpa henti.
            result = original_analyze(response, payload, **kwargs)
            result["vulnerability"] = "sqli"
            return result

        analyzer.analyze = analyze
        from training_loop import run_episode
        record, _next_state, _reward, verification = run_episode(
            agent, self.generator, client, analyzer, RewardSystem(),
            current_state=("2xx", 1, 0, 0, 0, 0, 0, 0),
        )
        self.assertEqual(record["rejected_candidate"], "sqli")
        self.assertEqual(record["vulnerability"], "none")
        self.assertFalse(record["verified"])
        # Hanya satu kontrol yang benar-benar terkirim (kegagalan koneksi
        # pada probe wildcard tidak menambah request).
        self.assertLessEqual(verification, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
