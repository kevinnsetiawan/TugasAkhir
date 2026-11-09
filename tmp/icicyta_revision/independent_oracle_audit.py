"""Independent, detector-blind audit of the 120 configured Juice Shop actions.

The audit does not import ResponseAnalyzer or ground_truth.py. It records raw
HTTP outcomes, compares search results with the product catalogue, checks
file responses against the actual packaged files, tests authentication bypass
through the returned token and official challenge state, and tests XSS through
real browser dialogs. Official challenge status is read from /api/Challenges.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "rl_pentest"
JUICE_SHOP = ROOT / "juice-shop"
OUT = Path(__file__).resolve().parent / "ground_truth_audit_independent_v2"
EVIDENCE = OUT / "evidence"
NODE = Path(r"C:\Users\Kevin Setiawan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe")
BASE_URL = "http://127.0.0.1:3001"
sys.path.insert(0, str(PROJECT))

from config import ENDPOINTS, XSS_PAGES, REQUEST_TIMEOUT  # noqa: E402
from engine.http_client import HTTPClient  # noqa: E402

PAYLOADS = json.loads((PROJECT / "data" / "payloads.json").read_text(encoding="utf-8"))
N_PAYLOADS = len(PAYLOADS)
SAFE_ENDPOINTS_FROM_SOURCE = {2, 5, 6, 7}
FILE_TARGETS = {
    10: JUICE_SHOP / "ftp" / "package.json.bak",
    11: JUICE_SHOP / "ftp" / "coupons_2013.md.bak",
    12: JUICE_SHOP / "ftp" / "suspicious_errors.yml",
}
CHALLENGE_KEYS_OF_INTEREST = {
    "loginAdminChallenge",
    "reflectedXssChallenge",
    "databaseSchemaChallenge",
    "forgottenBackupChallenge",
    "forgottenDevBackupChallenge",
    "nullByteChallenge",
    "misplacedSignatureFileChallenge",
}


def start_shop(run_id: str):
    OUT.mkdir(parents=True, exist_ok=True)
    stdout = open(OUT / f"{run_id}.stdout.log", "wb")
    stderr = open(OUT / f"{run_id}.stderr.log", "wb")
    env = os.environ.copy()
    env["PORT"] = "3001"
    process = subprocess.Popen(
        [str(NODE), "build/app.js"],
        cwd=JUICE_SHOP,
        env=env,
        stdout=stdout,
        stderr=stderr,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Juice Shop exited during {run_id}")
        try:
            response = requests.get(f"{BASE_URL}/api/Challenges", timeout=3)
            if response.status_code == 200:
                return process, stdout, stderr
        except requests.RequestException:
            pass
        time.sleep(1)
    process.terminate()
    raise TimeoutError(f"Juice Shop was not ready for {run_id}")


def stop_shop(handle) -> None:
    process, stdout, stderr = handle
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    stdout.close()
    stderr.close()


def challenge_state() -> dict[str, bool]:
    response = requests.get(f"{BASE_URL}/api/Challenges", timeout=10)
    response.raise_for_status()
    rows = response.json().get("data", [])
    return {row["key"]: bool(row.get("solved")) for row in rows if row.get("key")}


def independent_neutralized(payload: str) -> str:
    """Make a passive control without importing the prototype's mutator."""
    replacements = (
        (" onerror=alert(document.domain)", ""),
        (" onload=alert(1)", ""),
        ("<script>alert(document.domain)</script>", "<script></script>"),
        ("<img src=x onerror=alert(document.domain)>", "<img src=x>"),
        ("<svg onload=alert(1)>", "<svg></svg>"),
    )
    control = payload
    for active, passive in replacements:
        control = control.replace(active, passive)
    return control


def run_browser_probe(browser, endpoint_index: int, payload: str, label: str, attempts: int = 5) -> dict:
    page_path = XSS_PAGES[endpoint_index]
    url = f"{BASE_URL}{page_path.format(payload=quote(payload, safe=''))}"
    traces = []
    for attempt in range(1, attempts + 1):
        page = browser.new_page()
        dialogs: list[str] = []
        console: list[str] = []
        errors: list[str] = []
        network: list[dict[str, object]] = []

        def on_dialog(dialog):
            dialogs.append(dialog.message)
            dialog.dismiss()

        page.on("dialog", on_dialog)
        page.on("console", lambda msg: console.append(f"{msg.type}: {msg.text}") if len(console) < 20 else None)
        page.on("pageerror", lambda error: errors.append(str(error)) if len(errors) < 20 else None)
        page.on("request", lambda req: network.append({
            "method": req.method, "url": req.url[:400]
        }) if len(network) < 40 else None)
        status = None
        content_type = None
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            if response is not None:
                status = response.status
                content_type = response.headers.get("content-type")
            page.wait_for_timeout(1200)
            html_path = EVIDENCE / "browser" / f"{label}_attempt_{attempt:02d}.html"
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html = page.content()
            html_path.write_text(html, encoding="utf-8")
            screenshot = None
            if dialogs:
                screenshot_path = EVIDENCE / "screenshots" / f"{label}_attempt_{attempt:02d}.png"
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot_path), full_page=True)
                screenshot = str(screenshot_path.relative_to(OUT))
            traces.append({
                "attempt": attempt,
                "http_status": status,
                "content_type": content_type,
                "dialog_messages": dialogs,
                "dialog_executed": bool(dialogs),
                "console": console,
                "page_errors": errors,
                "requests": network,
                "dom_snapshot": str(html_path.relative_to(OUT)),
                "dom_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
                "screenshot": screenshot,
            })
        except Exception as error:  # evidence audit records, rather than hides, browser failures
            traces.append({
                "attempt": attempt,
                "http_status": status,
                "content_type": content_type,
                "dialog_messages": dialogs,
                "dialog_executed": bool(dialogs),
                "console": console,
                "page_errors": errors + [str(error)],
                "requests": network,
                "dom_snapshot": None,
                "dom_sha256": None,
                "screenshot": None,
            })
        finally:
            page.close()
    return {
        "url": url,
        "attempt_count": attempts,
        "dialog_executed": any(trace["dialog_executed"] for trace in traces),
        "dialog_messages": [message for trace in traces for message in trace["dialog_messages"]],
        "page_errors": [error for trace in traces for error in trace["page_errors"]],
        "attempts": traces,
    }


def send_action(endpoint_index: int, payload: str):
    client = HTTPClient(BASE_URL, endpoints=ENDPOINTS, timeout=REQUEST_TIMEOUT)
    try:
        return client.send_payload(payload, endpoint_index=endpoint_index)
    finally:
        client.session.close()


def save_body(action_index: int, endpoint_index: int, payload_index: int, response) -> dict:
    content = response.content or b""
    text = response.text or ""
    body_path = None
    raw_body_path = None
    if endpoint_index in {0, 1, 3, 4} or payload_index in FILE_TARGETS:
        body_path = EVIDENCE / "http" / f"action_{action_index:03d}.txt"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        # Do not persist a live authentication credential in the evidence bundle.
        safe_text = text
        token_redacted = False
        if endpoint_index == 4:
            try:
                data = json.loads(text)
                auth = data.get("authentication", {})
                if auth.get("token"):
                    auth["token"] = "[REDACTED]"
                    token_redacted = True
                    safe_text = json.dumps(data, ensure_ascii=False, indent=2)
            except (ValueError, AttributeError):
                pass
        body_path.write_text(safe_text, encoding="utf-8")
        if endpoint_index in {0, 1, 3}:
            raw_body_path = EVIDENCE / "http" / f"action_{action_index:03d}.bin"
            raw_body_path.write_bytes(content)
    return {
        "sha256": hashlib.sha256(content).hexdigest(),
        "response_bytes": len(content),
        "body_excerpt": text[:2500],
        "body_evidence_file": str(body_path.relative_to(OUT)) if body_path else None,
        "raw_body_file": str(raw_body_path.relative_to(OUT)) if raw_body_path else None,
        "token_redacted": bool(endpoint_index == 4 and body_path),
    }


def classify_independently(endpoint_index: int, payload_index: int, entry: dict,
                           response, body_text: str, browser_trace: dict | None,
                           all_product_ids: set[str], browser_control: dict | None = None) -> tuple[str, list[str]]:
    """Classify exact action outcome from direct effect evidence, not heuristics."""
    evidence: list[str] = []
    if endpoint_index in SAFE_ENDPOINTS_FROM_SOURCE:
        evidence.append("source-audited control endpoint: no matching vulnerable sink")
        return "negative", evidence

    # Keep actions outside the endpoint's independently tested input context
    # unknown. This preserves a conservative oracle for the cross-product cells
    # where, for example, a file-path payload was sent to the search route.
    in_scope = (
        (endpoint_index == 0 and (payload_index <= 4 or 6 <= payload_index <= 9))
        or (endpoint_index == 1 and payload_index in FILE_TARGETS)
        or (endpoint_index == 3 and 6 <= payload_index <= 9)
        or (endpoint_index == 4 and payload_index <= 5)
    )
    if not in_scope:
        return "unknown", ["payload and endpoint were outside the independently adjudicated input context"]

    if endpoint_index == 0 and entry["category"] == "sqli":
        try:
            data = response.json()
            rows = data.get("data", []) if isinstance(data, dict) else data
            returned_ids = {str(row.get("id")) for row in rows if isinstance(row, dict) and "id" in row}
        except (ValueError, TypeError):
            returned_ids = set()
        if all_product_ids and all_product_ids.issubset(returned_ids):
            evidence.append(f"search returned all {len(all_product_ids)} catalogue product IDs outside the benign filter")
            return "positive", evidence
        if response.status_code >= 500 and ("SQLITE_ERROR" in body_text or "syntax error" in body_text.lower()):
            evidence.append("crafted input produced a visible SQLite parser error in the server response")
            return "positive", evidence
        if payload_index == 4 and len(returned_ids) > 0:
            evidence.append(f"unescaped LIKE wildcard returned {len(returned_ids)} product records; benign and wildcard-neutralized controls are captured")
            return "positive", evidence
        if response.status_code < 500:
            evidence.append("no catalogue-wide data returned by this exact SQLi payload")
            return "negative", evidence
        return "unknown", ["server error without independently confirmed data exfiltration"]

    if endpoint_index == 4:
        try:
            data = response.json()
            token_present = bool(data.get("authentication", {}).get("token"))
        except (ValueError, AttributeError):
            token_present = False
        if token_present:
            evidence.append("login response contained an authentication token; token redacted in saved evidence")
            return "positive", evidence
        evidence.append("no authentication token or admin login result for this exact payload")
        return "negative", evidence

    if endpoint_index == 1:
        expected = FILE_TARGETS.get(payload_index)
        if expected is not None and expected.exists():
            expected_hash = hashlib.sha256(expected.read_bytes()).hexdigest()
            response_hash = hashlib.sha256(response.content or b"").hexdigest()
            if response_hash == expected_hash:
                evidence.append(f"raw response SHA-256 exactly matched packaged file {expected.name}")
                evidence.append(f"served content-type: {response.headers.get('content-type', '')}")
                return "positive", evidence
        if response.status_code < 500:
            evidence.append("no response body matched a protected packaged file")
            return "negative", evidence
        return "unknown", ["server error without a matching protected-file body"]

    if entry["category"] == "xss" and endpoint_index in XSS_PAGES:
        if (browser_trace and browser_trace.get("dialog_executed") and browser_control
                and not browser_control.get("dialog_executed") and not browser_control.get("page_errors")):
            successful = sum(1 for trace in browser_trace["attempts"] if trace["dialog_executed"])
            evidence.append(f"unmodified payload opened a JavaScript dialog in {successful}/{browser_trace['attempt_count']} Chromium attempts; neutralized control had no dialog")
            return "positive", evidence
        if browser_trace and not browser_trace.get("dialog_executed") and browser_control and not browser_control.get("dialog_executed") and not browser_trace.get("page_errors"):
            evidence.append(f"unmodified payload produced no JavaScript dialog in {browser_trace['attempt_count']} Chromium attempts")
            return "negative", evidence
        return "unknown", ["browser execution could not be conclusively observed"]

    if endpoint_index == 3:
        evidence.append("track-order identifier produced no independently observed browser execution")
        return "negative", evidence

    evidence.append("no independently defined exploit effect was observed")
    return "negative", evidence


def independent_control_payload(endpoint_index: int, payload_index: int, payload: str) -> str | None:
    """Choose a separately defined benign control for each exploit channel."""
    if endpoint_index == 0 and PAYLOADS[payload_index]["category"] == "sqli":
        if "%" in payload:
            return payload.replace("%", "")
        return payload.replace("'", "").replace("--", "").replace("SLEEP(5)", "SLEEP(0)") or "hello"
    if endpoint_index == 4 and PAYLOADS[payload_index]["category"] == "sqli":
        return json.dumps({"email": "admin@juice-sh.op", "password": "incorrect-independent-control"})
    if endpoint_index == 1 and payload_index in FILE_TARGETS:
        return payload.replace("%2500", ".")
    if PAYLOADS[payload_index]["category"] == "xss" and endpoint_index in XSS_PAGES:
        control = independent_neutralized(payload)
        return control if control != payload else None
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    challenge_file = JUICE_SHOP / "data" / "static" / "challenges.yml"
    challenge_catalog_sha256 = hashlib.sha256(challenge_file.read_bytes()).hexdigest()
    app_handle = start_shop("challenge_oracle")
    rows: list[dict[str, object]] = []
    browser_warnings = []
    try:
        baseline = send_action(0, "hello")
        baseline_products = baseline.json() if baseline.status_code == 200 else []
        all_products_response = requests.get(f"{BASE_URL}/api/Products", timeout=10)
        catalogue_json = all_products_response.json()
        all_products = catalogue_json.get("data", []) if isinstance(catalogue_json, dict) else catalogue_json
        all_product_ids = {str(row.get("id")) for row in all_products if isinstance(row, dict) and "id" in row}
        previous_challenges = challenge_state()

        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context()
            try:
                warmup_page = context.new_page()
                try:
                    warmup_page.goto(BASE_URL, wait_until="domcontentloaded", timeout=20000)
                    warmup_page.wait_for_timeout(1800)
                finally:
                    warmup_page.close()
                for action_index in range(len(ENDPOINTS) * N_PAYLOADS):
                    endpoint_index, payload_index = divmod(action_index, N_PAYLOADS)
                    entry = PAYLOADS[payload_index]
                    response = None
                    response_error = None
                    try:
                        response = send_action(endpoint_index, entry["payload"])
                        body_text = response.text or ""
                    except Exception as error:
                        response_error = str(error)
                        body_text = ""

                    browser_trace = None
                    control_trace = None
                    if response is not None and entry["category"] == "xss" and endpoint_index in XSS_PAGES:
                        browser_trace = run_browser_probe(
                            context, endpoint_index, entry["payload"], f"action_{action_index:03d}_test", attempts=5
                        )
                        control_payload = independent_control_payload(endpoint_index, payload_index, entry["payload"])
                        if control_payload:
                            control_trace = run_browser_probe(
                                context, endpoint_index, control_payload,
                                f"action_{action_index:03d}_control", attempts=5
                            )

                    after_challenges = challenge_state()
                    new_challenges = sorted(
                        key for key, solved in after_challenges.items()
                        if solved and not previous_challenges.get(key, False)
                    )
                    previous_challenges = after_challenges

                    if response is not None:
                        label, evidence = classify_independently(
                            endpoint_index, payload_index, entry, response,
                            body_text, browser_trace, all_product_ids, browser_control=control_trace
                        )
                        body_record = save_body(action_index, endpoint_index, payload_index, response)
                        response_meta = {
                            "status_code": response.status_code,
                            "content_type": response.headers.get("content-type"),
                            **body_record,
                        }
                    else:
                        label, evidence = "unknown", ["request failed: " + str(response_error)]
                        response_meta = {"status_code": None, "content_type": None, "error": response_error}

                    controls = []
                    control_payloads: list[tuple[str, str]] = []
                    if response is not None and endpoint_index == 0 and entry["category"] == "sqli":
                        control_payloads = [("benign", "hello")]
                        neutralized = independent_control_payload(endpoint_index, payload_index, entry["payload"])
                        if neutralized and neutralized != "hello":
                            control_payloads.append(("neutralized", neutralized))
                    elif label == "positive" and response is not None and entry["category"] != "xss":
                        neutralized = independent_control_payload(endpoint_index, payload_index, entry["payload"])
                        if neutralized:
                            control_payloads = [("neutralized", neutralized)]

                    for control_kind, control_payload in control_payloads:
                        try:
                            control = send_action(endpoint_index, control_payload)
                            control_body = control.content or b""
                            control_hash = hashlib.sha256(control_body).hexdigest()
                            control_file = EVIDENCE / "controls" / f"action_{action_index:03d}_{control_kind}.bin"
                            control_file.parent.mkdir(parents=True, exist_ok=True)
                            if endpoint_index != 4:
                                control_file.write_bytes(control_body)
                            control_details = {
                                "kind": control_kind,
                                "payload": control_payload,
                                "status_code": control.status_code,
                                "content_type": control.headers.get("content-type"),
                                "body_bytes": len(control_body),
                                "body_excerpt": (control.text or "")[:1000],
                                "sha256": control_hash,
                                "raw_body_file": str(control_file.relative_to(OUT)) if endpoint_index != 4 else None,
                            }
                            if endpoint_index == 0:
                                control_json = control.json()
                                control_data = control_json.get("data", []) if isinstance(control_json, dict) else control_json
                                control_details["returned_records"] = len(control_data) if isinstance(control_data, list) else None
                            if endpoint_index == 4:
                                try:
                                    control_details["authentication_token_present"] = bool(
                                        control.json().get("authentication", {}).get("token")
                                    )
                                except (ValueError, AttributeError):
                                    control_details["authentication_token_present"] = False
                            controls.append(control_details)
                        except Exception as error:
                            controls.append({"kind": control_kind, "payload": control_payload, "error": str(error)})

                    rows.append({
                        "action_index": action_index,
                        "endpoint_index": endpoint_index,
                        "endpoint": ENDPOINTS[endpoint_index]["path"],
                        "payload_index": payload_index,
                        "payload_name": entry["name"],
                        "payload_category": entry["category"],
                        "payload": entry["payload"],
                        "independent_label": label,
                        "evidence": evidence,
                        "response": response_meta,
                        "official_challenge_status_changes": new_challenges,
                        "browser_test": browser_trace,
                        "browser_control": control_trace,
                        "http_controls": controls,
                    })
                    if action_index % 20 == 19:
                        print(f"audit actions {action_index + 1}/120", flush=True)
            finally:
                context.close()
                browser.close()
    finally:
        stop_shop(app_handle)

    positives = [row for row in rows if row["independent_label"] == "positive"]
    negatives = [row for row in rows if row["independent_label"] == "negative"]
    unknown = [row for row in rows if row["independent_label"] == "unknown"]
    known_challenges = {
        key for row in rows for key in row["official_challenge_status_changes"]
    }
    audit = {
        "audit_id": "official_challenge_and_direct_effect_v2",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "juice_shop_version": "20.2.0",
        "juice_shop_commit": "1618a611b173b4bf114028e6e02549950606e29d",
        "challenge_catalog_path": str(challenge_file.relative_to(ROOT)),
        "challenge_catalog_sha256": challenge_catalog_sha256,
        "official_challenge_count": 116,
        "official_challenges_newly_solved_during_audit": sorted(known_challenges),
        "total_actions": len(rows),
        "positive": len(positives),
        "negative": len(negatives),
        "unknown": len(unknown),
        "positive_action_indices": [r["action_index"] for r in positives],
        "negative_action_indices": [r["action_index"] for r in negatives],
        "unknown_action_indices": [r["action_index"] for r in unknown],
        "all_product_ids_count": len(all_product_ids),
        "control_policy": "independently chosen benign search, invalid-password, extension-normalized file, and handler-neutralized browser controls",
        "detector_blind": True,
        "response_analyzer_imported": False,
        "existing_ground_truth_imported": False,
        "limitations": [
            "This audit is independent of the ResponseAnalyzer implementation but was conducted by the paper's authors, not an external second reviewer.",
            "Official scoreboard events, direct product-data evidence, exact packaged-file comparison, and five repeated unmodified JavaScript dialog checks with five neutralized-control checks were used as oracle channels.",
        ],
    }
    (OUT / "independent_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    with (OUT / "independent_audit_actions.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == "__main__":
    main()
