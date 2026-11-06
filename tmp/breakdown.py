import csv, io, subprocess, statistics, json
def load(path=None, git=None):
    txt = subprocess.run(["git","show",git],capture_output=True,text=True).stdout if git else open(path,encoding="utf-8").read()
    return list(csv.DictReader(io.StringIO(txt)))
for tag, rows, dur in [("QL Oct 9 (HEAD)", load(git="HEAD:rl_pentest/results/log_ql.csv"), 143.64),
                       ("QL Oct 23 (now) ", load("rl_pentest/results/log_ql.csv"), 203.37),
                       ("DQN Oct 9 (HEAD)", load(git="HEAD:rl_pentest/results/log_dqn.csv"), 145.81),
                       ("DQN Oct 16 (now) ", load("rl_pentest/results/log_dqn.csv"), 190.53)]:
    rt = sum(float(r["response_time"]) for r in rows)
    print(f"{tag}: wall={dur:7.2f}s | waktu_HTTP={rt:6.1f}s ({rt/dur*100:4.1f}%) | overhead_nonHTTP={dur-rt:6.1f}s ({(dur-rt)/dur*100:4.1f}%)")
