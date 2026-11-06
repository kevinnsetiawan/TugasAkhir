import subprocess, json
for f in ["rl_pentest/results/summary_ql.json", "rl_pentest/results/summary_dqn.json"]:
    commits = subprocess.run(["git","log","--all","--format=%h|%ci|%s","--",f],capture_output=True,text=True).stdout.strip().splitlines()
    print("="*100); print(f)
    for c in commits:
        h, date, subj = c.split("|",2)
        raw = subprocess.run(["git","show",f"{h}:{f}"],capture_output=True,text=True).stdout
        if not raw.strip(): continue
        try: d = json.loads(raw)
        except Exception: print(h, "unparsable"); continue
        print(f"  {h} {date[:16]} | eps={d.get('total_episodes')} vuln={d.get('total_vulnerabilities')} "
              f"rt={d.get('average_response_time')} dur={d.get('training_duration_seconds')} "
              f"states={d.get('states_visited')} nav={d.get('browser_navigations')} verif={d.get('verification_requests')}")
