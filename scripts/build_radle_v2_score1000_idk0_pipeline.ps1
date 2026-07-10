param(
    [string]$InputMaster = "outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/radle_v2_final_long_master.csv",
    [string]$OutDir = "outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0"
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

    Write-Host "[RUN] Score1000 IDK0 CSV generation"
    Invoke-PythonStep @(
        "scripts/make_radle_v2_likert5_score1000_csvs_IDK0.py",
        "--clean-master",
        $CleanMaster,
        "--clean-receipt",
        $CleanReceipt,
        "--out-dir",
        $OutDir,
        "--idk-score",
        "0"
    )

    Write-Host "[RUN] Score1000 IDK0 audit"
    Invoke-PythonStep @("scripts/audit_radle_v2_likert5_score1000_csvs_IDK0.py", "--out-dir", $OutDir, "--idk-score", "0")

    $PanelDir = Join-Path $OutDir "handwritten_panels_IDK0"
    $VariantDir = Join-Path $OutDir "handwritten_panels_model_group_color_final_IDK0"
    $Panel5Dir = Join-Path $VariantDir "p5_IDK0"

    Write-Host "[RUN] Score2000 IDK0 panel stats"
    Invoke-PythonStep @(
        "scripts/radle_v2_score1000_panel_stats_IDK0.py",
        "--score-root",
        $OutDir,
        "--out-dir",
        $PanelDir
    )

    Write-Host "[RUN] Score2000 IDK0 SVG variants"
    Invoke-PythonStep @(
        "scripts/make_radle_v2_score1000_panel23_svg_IDK0.py",
        "--mode",
        "model-group-color-final",
        "--source-panel-dir",
        $PanelDir,
        "--out-dir",
        $VariantDir,
        "--idk-score",
        "0"
    )

    Write-Host "[RUN] Score2000 IDK0 Panel 5.4 logo placement"
    Invoke-PythonStep @(
        "scripts/make_radle_v2_score1000_panel5_logo_placement_contact_sheet_IDK0.py",
        "--source-panel-dir",
        $VariantDir,
        "--out-dir",
        $Panel5Dir,
        "--idk-score",
        "0"
    )

    Write-Host "[RUN] Score2000 IDK0 SVG audit"
    Invoke-PythonStep @(
        "scripts/audit_radle_v2_score1000_panel23_IDK0.py",
        "--mode",
        "model-group-color-final",
        "--score-root",
        $OutDir,
        "--out-dir",
        $VariantDir,
        "--idk-score",
        "0"
    )

    Write-Host "[PASS] RadLE v2 Score1000 IDK0 pipeline complete"
}
finally {
    Pop-Location
}
