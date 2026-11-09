# ============================================
# Script Auto-Correction Bab 4 Skripsi
# ============================================
# Memperbaiki angka-angka di 07_bab4.tex agar sesuai dengan output sistem aktual
# Data source: rl_pentest/results/summary_*.json

param(
    [string]$InputFile = "temp_extract_skripsi\07_bab4.tex",
    [string]$OutputFile = "temp_extract_skripsi\07_bab4_FIXED.tex"
)

Write-Host "`n[*] Starting Bab 4 Auto-Correction Script..." -ForegroundColor Cyan
Write-Host "[*] Input:  $InputFile" -ForegroundColor Gray
Write-Host "[*] Output: $OutputFile" -ForegroundColor Gray

# Backup original
if (Test-Path $InputFile) {
    Copy-Item $InputFile "$InputFile.BACKUP_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Host "[+] Backup created" -ForegroundColor Green
} else {
    Write-Host "[!] Error: Input file not found: $InputFile" -ForegroundColor Red
    exit 1
}

# Read file
$content = Get-Content $InputFile -Raw -Encoding UTF8

# ============================================
# CRITICAL CORRECTIONS (High Priority)
# ============================================

Write-Host "`n[1/12] Fixing DQN Cumulative Reward: 10.209 -> 9.503" -ForegroundColor Yellow
$content = $content -replace '\b10\.209\b', '9.503'
$content = $content -replace '\b10,209\b', '9.503'

Write-Host "[2/12] Fixing DQN Vuln Count: 12 -> 13" -ForegroundColor Yellow
# Hati-hati: hanya replace di konteks tabel comparison
$content = $content -replace '(\& \textbf\{14\} \& )12( \\\\)', '${1}13${2}'

Write-Host "[3/12] Fixing DQN XSS Count: 4 -> 5" -ForegroundColor Yellow
# Hanya di baris "Reflected XSS (DOM Verified)"
$content = $content -replace '(Reflected XSS.*?\& 5 \& )4( \\\\)', '${1}5${2}'

Write-Host "[4/12] Fixing Reward Ratio: 2,70 -> 2,51" -ForegroundColor Yellow
$content = $content -replace '2,70 kali lipat', '2,51 kali lipat'
$content = $content -replace '2\.70 kali lipat', '2,51 kali lipat'

# ============================================
# MEDIUM PRIORITY CORRECTIONS
# ============================================

Write-Host "[5/12] Fixing QL Cumulative Reward: 3.785 -> 3.783" -ForegroundColor Yellow
$content = $content -replace '\b3\.785\b', '3.783'
$content = $content -replace '\b3,785\b', '3.783'

Write-Host "[6/12] Fixing QL State Count: 27 -> 25" -ForegroundColor Yellow
$content = $content -replace '27 state unik', '25 state unik'
$content = $content -replace '\b27\b state', '25 state'
# Also fix "23 state" to "25 state" for consistency
$content = $content -replace '23 state unik', '25 state unik'
$content = $content -replace '\b23\b state', '25 state'

Write-Host "[7/12] Fixing QL Training Duration: 154,23s -> 142,55s" -ForegroundColor Yellow
$content = $content -replace '154,23 detik', '142,55 detik'
$content = $content -replace '154\.23 detik', '142,55 detik'

Write-Host "[8/12] Fixing DQN Training Duration: 160,04s -> 146,95s" -ForegroundColor Yellow
$content = $content -replace '160,04 detik', '146,95 detik'
$content = $content -replace '160\.04 detik', '146,95 detik'

Write-Host "[9/12] Fixing QL Total Transactions: 1.640 -> 1.639" -ForegroundColor Yellow
$content = $content -replace '1\.640 \& 1\.636', '1.639 & 1.637'
$content = $content -replace '1,640 \& 1,636', '1.639 & 1.637'

Write-Host "[10/12] Fixing DQN Req/Vuln: 132,08 -> 121,92" -ForegroundColor Yellow
$content = $content -replace '132,08\b', '121,92'
$content = $content -replace '132\.08\b', '121,92'

# ============================================
# LOW PRIORITY CORRECTIONS
# ============================================

Write-Host "[11/12] Fixing QL Subset Requests: 1.223 -> 1.226" -ForegroundColor Yellow
$content = $content -replace '1\.223\b', '1.226'
$content = $content -replace '1,223\b', '1.226'

Write-Host "[12/12] Fixing QL Subset Req/Vuln: 122,30 -> 122,60" -ForegroundColor Yellow
$content = $content -replace '122,30\b', '122,60'
$content = $content -replace '122\.30\b', '122,60'

Write-Host "[+] Fixing Efficiency Ratio: 6,48 -> 6,46 (minor)" -ForegroundColor Yellow
$content = $content -replace '6,48\b', '6,46'
$content = $content -replace '6\.48\b', '6,46'

# ============================================
# TEXT CORRECTIONS (Analytical)
# ============================================

Write-Host "`n[*] Applying text corrections..." -ForegroundColor Cyan

# Fix: "12 temuan terverifikasi" -> "13 temuan terverifikasi"
$content = $content -replace 'DQN memperoleh 12 temuan terverifikasi', 'DQN memperoleh 13 temuan terverifikasi'

# Fix closing statement
$oldClosing = 'Q-Learning memperoleh 14 temuan terverifikasi dan DQN memperoleh 12 temuan terverifikasi'
$newClosing = 'Q-Learning memperoleh 14 temuan terverifikasi (6 SQLi, 5 XSS, 3 Fuzz) dan DQN memperoleh 13 temuan terverifikasi (6 SQLi, 5 XSS, 2 Fuzz)'
$content = $content -replace [regex]::Escape($oldClosing), $newClosing

# ============================================
# WRITE OUTPUT
# ============================================

Write-Host "`n[*] Writing corrected file..." -ForegroundColor Cyan
$content | Out-File -FilePath $OutputFile -Encoding UTF8 -NoNewline

Write-Host "[+] Corrections applied successfully!" -ForegroundColor Green
Write-Host "[+] Output saved to: $OutputFile" -ForegroundColor Green

# ============================================
# VERIFICATION REPORT
# ============================================

Write-Host "`n=== VERIFICATION REPORT ===" -ForegroundColor Cyan
Write-Host "Please manually verify the following:" -ForegroundColor Yellow
Write-Host "  [ ] QL Reward: 3.783 (was 3.785)" -ForegroundColor Gray
Write-Host "  [ ] QL States: 25 (was 27 or 23)" -ForegroundColor Gray
Write-Host "  [ ] QL Duration: 142,55s (was 154,23s)" -ForegroundColor Gray
Write-Host "  [ ] QL Total Txn: 1.639 (was 1.640)" -ForegroundColor Gray
Write-Host "  [ ] DQN Reward: 9.503 (was 10.209) ** CRITICAL **" -ForegroundColor Red
Write-Host "  [ ] DQN Vuln: 13 (was 12) ** CRITICAL **" -ForegroundColor Red
Write-Host "  [ ] DQN XSS: 5 (was 4)" -ForegroundColor Gray
Write-Host "  [ ] DQN Duration: 146,95s (was 160,04s)" -ForegroundColor Gray
Write-Host "  [ ] DQN Req/Vuln: 121,92 (was 132,08)" -ForegroundColor Gray
Write-Host "  [ ] Reward Ratio: 2,51x (was 2,70x)" -ForegroundColor Gray
Write-Host "  [ ] QL Subset Req: 1.226 (was 1.223)" -ForegroundColor Gray
Write-Host "  [ ] Efficiency: 6,46x (was 6,48x)" -ForegroundColor Gray

Write-Host "`n[!] NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. Open $OutputFile in LaTeX editor" -ForegroundColor White
Write-Host "  2. Manually verify critical changes (DQN reward & vuln count)" -ForegroundColor White
Write-Host "  3. Search for remaining '12 temuan' and replace with '13 temuan'" -ForegroundColor White
Write-Host "  4. Compile: pdflatex 00_MAIN_ProposalTA.tex" -ForegroundColor White
Write-Host "  5. Check for unresolved references (??)" -ForegroundColor White

Write-Host "`n[✓] Script completed!" -ForegroundColor Green
