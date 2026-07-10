param(
    [string]$ScoreRoot = "outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\likert5_score1000",
    [string]$OutDir = "outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\likert5_score1000\handwritten_panels",
    [switch]$SkipVisualQa
)

$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [string]$Name,
        [string[]]$Command
    )
    Write-Host "[RUN] $Name"
    $exe = $Command[0]
    $cmdArgs = @()
    if ($Command.Length -gt 1) {
        $cmdArgs = $Command[1..($Command.Length - 1)]
    }
    & $exe @cmdArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name"
    }
}

Run-Step "Score1000 Panel 2/3 stats" @("py", "-3.11", "scripts\radle_v2_score1000_panel_stats.py", "--score-root", $ScoreRoot, "--out-dir", $OutDir)
Run-Step "Score1000 Panel 2/3 SVG generation" @("py", "-3.11", "scripts\make_radle_v2_score1000_panel23_svg.py", "--score-root", $ScoreRoot, "--out-dir", $OutDir)

$AuditCommand = @("py", "-3.11", "scripts\audit_radle_v2_score1000_panel23.py", "--score-root", $ScoreRoot, "--out-dir", $OutDir)
if ($SkipVisualQa) {
    $AuditCommand += "--skip-visual-qa"
}
Run-Step "Score1000 Panel 2/3 audit" $AuditCommand

Write-Host "[PASS] RadLE v2 Score1000 Panel 2/3 build complete"
