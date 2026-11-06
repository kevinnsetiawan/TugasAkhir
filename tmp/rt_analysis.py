import csv, io, json, subprocess, statistics
from datetime import datetime

def load(path=None, git=None):
    if git:
        txt = subprocess.run(["git","show",git],capture_output=True,text=True).stdout
    else:
        txt = open(path, encoding="utf-8").read()
    return list(csv.DictReader(io.StringIO(txt)))

def stats(rows, tag):
    rt = [float(r["response_time"]) for r in rows]
    ts = [datetime.fromisoformat(r["timestamp"].replace("Z","+00:00")) for r in rows]
    span = (ts[-1]-ts[0]).total_seconds()
    print(f"{tag}: n={len(rows)} mean_rt={statistics.mean(rt):.4f}s median={statistics.median(rt):.4f} p90={sorted(rt)[int(.9*len(rt))]:.4f} max={max(rt):.3f} wall_span={span:.1f}s")
    # per endpoint
    per = {}
    for r in rows:
        per.setdefault(r["endpoint_index"], []).append(float(r["response_time"]))
    for ep in sorted(per):
        v = per[ep]
        print(f"   ep{ep}: n={len(v):4d} mean={statistics.mean(v):.4f} p95={sorted(v)[int(.95*len(v))]:.4f}")
    print(f"   window: {ts[0].isoformat()} -> {ts[-1].isoformat()}")

stats(load("rl_pentest/results/log_ql.csv"), "QL now (203s)")
stats(load(git="HEAD:rl_pentest/results/log_ql.csv"), "QL HEAD (143s)")
stats(load("rl_pentest/results/log_dqn.csv"), "DQN now (190s)")
stats(load(git="HEAD:rl_pentest/results/log_dqn.csv"), "DQN HEAD (145s)")
