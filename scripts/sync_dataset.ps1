# Sinkronisasi dataset dari sumber asli ke folder dataset/
# Jalankan dari root proyek: powershell -ExecutionPolicy Bypass -File scripts\sync_dataset.ps1
$base = "dataset"
$dirs = "$base\input", "$base\ql", "$base\dqn", "$base\qtable", "$base\zap", "$base\comparison"
foreach ($d in $dirs) { New-Item -ItemType Directory -Path $d -Force | Out-Null }

Copy-Item "rl_pentest\data\payloads.json"                   "$base\input\payloads.json" -Force
Copy-Item "rl_pentest\results\log_ql.csv"                   "$base\ql\log_ql.csv" -Force
Copy-Item "rl_pentest\results\summary_ql.json"              "$base\ql\summary_ql.json" -Force
Copy-Item "rl_pentest\results\log_dqn.csv"                  "$base\dqn\log_dqn.csv" -Force
Copy-Item "rl_pentest\results\summary_dqn.json"             "$base\dqn\summary_dqn.json" -Force
Copy-Item "rl_pentest\qtable\q_table.json"                  "$base\qtable\q_table.json" -Force
Copy-Item "rl_pentest\qtable\dqn_model.pt"                  "$base\qtable\dqn_model.pt" -Force
Copy-Item "rl_pentest\results\zap_controlled_report.json"   "$base\zap\zap_controlled_report.json" -Force
if (Test-Path "rl_pentest\results\zap_report.json") {
    Copy-Item "rl_pentest\results\zap_report.json"          "$base\zap\zap_report.json" -Force
}
Copy-Item "zap_comparison_report.json"                      "$base\comparison\zap_comparison_report.json" -Force

Write-Output "[+] Dataset tersinkronisasi di $base"