param(
    [string]$InputMaster = "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv",
    [string]$OutDir = "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$CleanMaster = Join-Path $OutDir "radle_v2_clean_adjudication_master.csv"
$CleanReceipt = Join-Path $OutDir "adjudication_master_cleanup_receipt.json"

function Invoke-PythonStep {
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$Arguments
    )

    & py -3.11 @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python step failed with exit code $LASTEXITCODE`: py -3.11 $($Arguments -join ' ')"
    }
}

Push-Location $RepoRoot
try {
    Write-Host "[RUN] clean adjudication master"
    Invoke-PythonStep @("scripts/build_radle_v2_clean_adjudication_master.py", "--input", $InputMaster, "--out-dir", $OutDir)

    Write-Host "[RUN] Score1000 CSV generation"
    Invoke-PythonStep @(
        "scripts/make_radle_v2_likert5_score1000_csvs.py",
        "--clean-master",
        $CleanMaster,
        "--clean-receipt",
        $CleanReceipt,
        "--out-dir",
        $OutDir
    )

    Write-Host "[RUN] Score1000 audit"
    Invoke-PythonStep @("scripts/audit_radle_v2_likert5_score1000_csvs.py", "--out-dir", $OutDir)

    Write-Host "[PASS] RadLE v2 Score1000 pipeline complete"
}
finally {
    Pop-Location
}
