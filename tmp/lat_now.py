import sys, time, statistics
sys.path.insert(0, "rl_pentest")
from config import BASE_URL, ENDPOINTS, REQUEST_TIMEOUT
from engine.http_client import HTTPClient

c = HTTPClient(BASE_URL, endpoints=ENDPOINTS, timeout=REQUEST_TIMEOUT)
print("base", BASE_URL)
for idx in range(len(ENDPOINTS)):
    ts = []
    for _ in range(15):
        t0 = time.perf_counter()
        try:
            c.send_payload("hello", endpoint_index=idx)
        except RuntimeError as e:
            print(idx, "ERR", e); break
        ts.append(time.perf_counter() - t0)
    if ts:
        print(f"ep{idx}: n={len(ts)} median={statistics.median(ts)*1000:.1f}ms mean={statistics.mean(ts)*1000:.1f}ms min={min(ts)*1000:.1f} max={max(ts)*1000:.1f}")
