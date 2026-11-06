import csv, io, subprocess, statistics
def load(path=None, git=None):
    txt = subprocess.run(["git","show",git],capture_output=True,text=True).stdout if git else open(path,encoding="utf-8").read()
    return list(csv.DictReader(io.StringIO(txt)))
for tag, rows in [("QL now", load("rl_pentest/results/log_ql.csv")), ("QL old", load(git="HEAD:rl_pentest/results/log_ql.csv")),
                  ("DQN now", load("rl_pentest/results/log_dqn.csv")), ("DQN old", load(git="HEAD:rl_pentest/results/log_dqn.csv"))]:
    per={}
    for r in rows:
        per.setdefault(r["endpoint_index"],[]).append(int(r["response_length"]))
    print(tag, {k: round(statistics.mean(v)) for k,v in sorted(per.items())})
