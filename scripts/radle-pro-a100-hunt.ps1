[CmdletBinding()]
param(
    [string]$Project = "crashlab-synthetic",
    [switch]$Execute,
    [switch]$PreflightOnly,
    [string]$StopFile = "",
    [string]$LogPath = "",
    [int]$CreatePollMinutes = 6,
    [int]$PollSeconds = 15,
    [int]$VerifyPollSeconds = 30,
    [int]$SweepRestSeconds = 20,
    [int]$MaxTransientRetries = 6
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProfileName = "a100-40"
$InstancePrefix = "radle-pro-a100"
$MachineType = "a2-highgpu-1g"
$AcceleratorType = "NVIDIA_TESLA_A100"
$AcceleratorCount = 1
$QuotaMetric = "NVIDIA_A100_GPUS"
$CpuQuotaMetrics = @("CPUS", "A2_CPUS")
$RequiredCpus = 12
$Zones = @(
    "us-central1-a",
    "us-central1-b",
    "us-central1-c",
    "us-central1-f",
    "us-east1-b",
    "us-west1-b",
    "us-west4-b",
    "europe-west4-a",
    "europe-west4-b",
    "asia-northeast1-a",
    "asia-northeast1-c",
    "asia-northeast3-a",
    "asia-northeast3-b",
    "asia-southeast1-a",
    "asia-southeast1-b",
    "asia-southeast1-c"
)

$StopHuntStates = @("PROVISIONING", "STARTING", "INITIALIZING", "STAGING", "ACTIVE")
$TerminalCleanupStates = @("FAILED", "DELETED")
$ManualInspectionStates = @("STOPPING", "STOPPED", "ERROR")
$NeverDeleteNames = @("medical-master-radfm", "medical-test-l4", "medical-master-a100")

$RepoRoot = Split-Path -Parent $PSScriptRoot
$OutputDir = Join-Path $RepoRoot "outputs\gcp_hunt"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

if (-not $StopFile) {
    $StopFile = Join-Path $OutputDir "STOP_ALL_HUNTS"
}
if (-not $LogPath) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $LogPath = Join-Path $OutputDir "$ProfileName`_hunt_$stamp.log"
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $line = "{0} [{1}] [{2}] {3}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"), $Level, $ProfileName, $Message
    Write-Host $line
    Add-Content -LiteralPath $LogPath -Value $line
}

function Invoke-Gcloud {
    param(
        [string[]]$GcloudArgs,
        [switch]$AllowFailure
    )
    $output = & gcloud @GcloudArgs 2>&1 | ForEach-Object { $_.ToString() }
    $code = $LASTEXITCODE
    $text = ($output -join [Environment]::NewLine).Trim()
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "gcloud $($GcloudArgs -join ' ') failed with exit $code`n$text"
    }
    [pscustomobject]@{ Code = $code; Text = $text }
}

function Get-RegionFromZone {
    param([string]$Zone)
    return ($Zone -replace "-[a-z]$", "")
}

function Get-GcloudFailureClass {
    param([string]$Text)
    if (-not $Text) {
        return "UNKNOWN"
    }
    if ($Text -match "429|RATE_LIMIT_EXCEEDED|Rate limit exceeded|Too many requests|The service is currently unavailable|503") {
        return "TRANSIENT_API"
    }
    if ($Text -match "Quota exceeded for quota metric|QUOTA_EXCEEDED|Quota 'CPUS' exceeded|Insufficient regional quota|quota.*exceeded") {
        return "QUOTA"
    }
    if ($Text -match "ZONE_RESOURCE_POOL_EXHAUSTED|ZONE_RESOURCE_POOL_EXHAUSTED_WITH_DETAILS|does not have enough resources available|out of stock") {
        return "STOCKOUT"
    }
    if ($Text -match "INVALID_FIELD_VALUE|Machine type '.*' is not supported|requested accelerator type '.*' is not available|combination of machine type .* accelerator .* invalid|not supported in zone|accelerator type .* is not available") {
        return "UNSUPPORTED_SHAPE"
    }
    if ($Text -match "LOCATION_POLICY_VIOLATED|PERMISSION_DENIED|constraints/gcp.resourceLocations|not in the scope of the organization policy|restricted by organization policy") {
        return "LOCATION_POLICY"
    }
    return "UNKNOWN"
}

function Start-RateLimitBackoff {
    param([int]$Attempt)
    $baseSeconds = [Math]::Min(60, [int][Math]::Pow(2, $Attempt))
    $jitterMilliseconds = Get-Random -Minimum 0 -Maximum 500
    Write-Log "Transient API/rate-limit failure. Backing off for $baseSeconds seconds + $jitterMilliseconds ms before retry $Attempt of $MaxTransientRetries." "WARN"
    Start-Sleep -Seconds $baseSeconds
    Start-Sleep -Milliseconds $jitterMilliseconds
}

function New-AttemptName {
    $stamp = Get-Date -Format "MMddHHmmss"
    $suffix = Get-Random -Minimum 1000 -Maximum 9999
    return "$InstancePrefix-$stamp-$suffix"
}

function Get-WorkbenchInstance {
    param(
        [string]$Name,
        [string]$Zone
    )
    $result = Invoke-Gcloud -GcloudArgs @(
        "workbench", "instances", "describe", $Name,
        "--location=$Zone",
        "--project=$Project",
        "--format=json"
    ) -AllowFailure

    if ($result.Code -ne 0) {
        if ($result.Text -match "NOT_FOUND|not found|was not found") {
            return $null
        }
        return [pscustomobject]@{
            Name = $Name
            Zone = $Zone
            State = "DESCRIBE_ERROR"
            ProxyUri = ""
            Error = $result.Text
        }
    }

    if (-not $result.Text) {
        return $null
    }

    $raw = $result.Text | ConvertFrom-Json
    $state = ""
    $proxyUri = ""
    if ($raw.PSObject.Properties.Name -contains "state") {
        $state = [string]$raw.state
    }
    if ($raw.PSObject.Properties.Name -contains "proxyUri") {
        $proxyUri = [string]$raw.proxyUri
    }

    [pscustomobject]@{
        Name = $Name
        Zone = $Zone
        State = $state
        ProxyUri = $proxyUri
        Error = ""
    }
}

function Get-QuotaRows {
    param([string]$Region)
    $result = Invoke-Gcloud -GcloudArgs @(
        "compute", "regions", "describe", $Region,
        "--project=$Project",
        "--format=json"
    ) -AllowFailure

    if ($result.Code -ne 0) {
        return @([pscustomobject]@{
            Region = $Region
            Metric = "REGION_DESCRIBE_ERROR"
            Limit = 0.0
            Usage = 0.0
            Headroom = 0.0
            Error = $result.Text
        })
    }

    $regionJson = $result.Text | ConvertFrom-Json
    @($regionJson.quotas | Where-Object { $_.metric -eq $QuotaMetric -or $CpuQuotaMetrics -contains $_.metric } | ForEach-Object {
        $limit = [double]$_.limit
        $usage = [double]$_.usage
        [pscustomobject]@{
            Region = $Region
            Metric = [string]$_.metric
            Limit = $limit
            Usage = $usage
            Headroom = ($limit - $usage)
            Error = ""
        }
    })
}

function Test-QuotaForZone {
    param([string]$Zone)
    $region = Get-RegionFromZone $Zone
    $rows = @(Get-QuotaRows -Region $region)
    $gpu = $rows | Where-Object { $_.Metric -eq $QuotaMetric } | Select-Object -First 1
    $cpuRows = @($rows | Where-Object { $CpuQuotaMetrics -contains $_.Metric })

    if (-not $gpu) {
        return [pscustomobject]@{ Ok = $false; Reason = "No $QuotaMetric row visible in $region"; Rows = $rows }
    }
    if ($gpu.Headroom -lt $AcceleratorCount) {
        return [pscustomobject]@{ Ok = $false; Reason = "$QuotaMetric headroom is $($gpu.Headroom), need $AcceleratorCount"; Rows = $rows }
    }
    $blockedCpu = $cpuRows | Where-Object { $_.Headroom -lt $RequiredCpus } | Select-Object -First 1
    if ($blockedCpu) {
        return [pscustomobject]@{ Ok = $false; Reason = "$($blockedCpu.Metric) headroom is $($blockedCpu.Headroom), need $RequiredCpus"; Rows = $rows }
    }
    return [pscustomobject]@{ Ok = $true; Reason = "Quota headroom OK"; Rows = $rows }
}

function Write-StopFile {
    param(
        [string]$Name,
        [string]$Zone,
        [string]$State
    )
    $payload = [pscustomobject]@{
        timestamp = (Get-Date).ToString("o")
        profile = $ProfileName
        instance = $Name
        zone = $Zone
        machine_type = $MachineType
        accelerator_type = $AcceleratorType
        accelerator_count = $AcceleratorCount
        state = $State
        note = "Stop all new hunt attempts; verify this Workbench instance before deleting anything."
    }
    if (Test-Path -LiteralPath $StopFile) {
        Write-Log "Stop file already exists at $StopFile. Leaving it untouched." "WARN"
        return
    }
    $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StopFile -Encoding UTF8
    Write-Log "Created stop file at $StopFile" "SUCCESS"
}

function Remove-CurrentAttempt {
    param(
        [string]$Name,
        [string]$Zone,
        [string]$State
    )
    if ($NeverDeleteNames -contains $Name) {
        Write-Log "Refusing to delete protected instance name $Name." "ERROR"
        return
    }
    Write-Log "Deleting current failed attempt only: name=$Name zone=$Zone state=$State" "WARN"
    $delete = Invoke-Gcloud -GcloudArgs @(
        "workbench", "instances", "delete", $Name,
        "--location=$Zone",
        "--project=$Project",
        "--quiet",
        "--async"
    ) -AllowFailure
    if ($delete.Code -eq 0) {
        Write-Log "Delete submitted for current failed attempt $Name in $Zone."
    } else {
        Write-Log "Delete returned exit $($delete.Code): $($delete.Text)" "WARN"
    }
}

function Wait-UntilUsable {
    param(
        [string]$Name,
        [string]$Zone
    )
    Write-Log "Verifying landed Workbench until ACTIVE with proxyUri: $Name in $Zone."
    while ($true) {
        $desc = Get-WorkbenchInstance -Name $Name -Zone $Zone
        if (-not $desc) {
            Write-Log "$Name disappeared from $Zone during verification. Manual inspection required." "ERROR"
            exit 4
        }
        Write-Log "Verification state: name=$Name zone=$Zone state=$($desc.State) proxyUri=$($desc.ProxyUri)"
        if ($desc.State -eq "ACTIVE" -and $desc.ProxyUri) {
            Write-Log "USABLE: $Name is ACTIVE in $Zone with proxyUri=$($desc.ProxyUri)" "SUCCESS"
            exit 0
        }
        if ($TerminalCleanupStates -contains $desc.State) {
            Write-Log "$Name reached terminal state $($desc.State) after landing. Manual inspection required before restart." "ERROR"
            exit 5
        }
        if ($ManualInspectionStates -contains $desc.State) {
            Write-Log "$Name reached state $($desc.State) after landing. Manual inspection required before restart." "ERROR"
            exit 5
        }
        Start-Sleep -Seconds $VerifyPollSeconds
    }
}

function Run-Preflight {
    Write-Log "Preflight starting. project=$Project machine=$MachineType accelerator=$AcceleratorType count=$AcceleratorCount stopFile=$StopFile"

    $activeProject = (Invoke-Gcloud -GcloudArgs @("config", "get-value", "project") -AllowFailure).Text
    Write-Log "gcloud active project: $activeProject"
    $activeAccount = (Invoke-Gcloud -GcloudArgs @("auth", "list", "--filter=status:ACTIVE", "--format=value(account)") -AllowFailure).Text
    Write-Log "gcloud active account: $activeAccount"

    foreach ($zone in $Zones) {
        $quota = Test-QuotaForZone -Zone $zone
        if ($quota.Ok) {
            Write-Log "Preflight quota OK for $zone"
        } else {
            Write-Log "Preflight quota/access warning for ${zone}: $($quota.Reason)" "WARN"
        }
    }
}

function Invoke-Attempt {
    param(
        [string]$Name,
        [string]$Zone
    )

    Write-Log "Attempting create: name=$Name zone=$Zone machine=$MachineType accelerator=$AcceleratorType count=$AcceleratorCount"
    $create = $null
    for ($retry = 1; $retry -le ($MaxTransientRetries + 1); $retry++) {
        $create = Invoke-Gcloud -GcloudArgs @(
            "workbench", "instances", "create", $Name,
            "--location=$Zone",
            "--project=$Project",
            "--machine-type=$MachineType",
            "--accelerator-type=$AcceleratorType",
            "--accelerator-core-count=$AcceleratorCount",
            "--boot-disk-size=200",
            "--boot-disk-type=PD_BALANCED",
            "--vm-image-project=cloud-notebooks-managed",
            "--vm-image-family=workbench-instances",
            "--install-gpu-driver",
            "--labels=radle-hunt=lingshu-radfm,hunt-profile=$ProfileName,managed-by=codex",
            "--async",
            "--quiet"
        ) -AllowFailure

        if ($create.Text) {
            Write-Log "Create output: $($create.Text)"
        }
        if ($create.Code -eq 0) {
            break
        }
        $failureClass = Get-GcloudFailureClass -Text $create.Text
        if ($failureClass -eq "TRANSIENT_API" -and $retry -le $MaxTransientRetries) {
            Start-RateLimitBackoff -Attempt $retry
            continue
        }
        break
    }

    if ($create.Code -ne 0) {
        $failureClass = Get-GcloudFailureClass -Text $create.Text
        switch ($failureClass) {
            "QUOTA" { Write-Log "QUOTA_FAILURE zone=$Zone. Stop this region/profile; administrative quota change needed. Not stockout." "WARN" }
            "LOCATION_POLICY" { Write-Log "LOCATION_POLICY_OR_PERMISSION zone=$Zone. Exclude this region/location. Not stockout." "WARN" }
            "UNSUPPORTED_SHAPE" { Write-Log "UNSUPPORTED_SHAPE zone=$Zone. Remove this zone for $MachineType/$AcceleratorType." "WARN" }
            "STOCKOUT" { Write-Log "STOCKOUT_CREATE_FAILURE zone=$Zone. Moving to next zone." "WARN" }
            "TRANSIENT_API" { Write-Log "TRANSIENT_API_FAILURE zone=$Zone persisted after $MaxTransientRetries retries. Longer cooldown or API quota review needed." "ERROR" }
            default { Write-Log "CREATE_ERROR zone=$Zone class=$failureClass exit=$($create.Code). Manual review may be needed." "ERROR" }
        }
        return
    }

    $deadline = (Get-Date).AddMinutes($CreatePollMinutes)
    while ((Get-Date) -lt $deadline) {
        $desc = Get-WorkbenchInstance -Name $Name -Zone $Zone
        if ($desc) {
            Write-Log "Post-create state: name=$Name zone=$Zone state=$($desc.State) proxyUri=$($desc.ProxyUri)"
            if ($desc.State -eq "DESCRIBE_ERROR") {
                $describeClass = Get-GcloudFailureClass -Text $desc.Error
                Write-Log "DESCRIBE_ERROR class=$describeClass error=$($desc.Error)" "WARN"
                if ($describeClass -eq "TRANSIENT_API") {
                    Start-RateLimitBackoff -Attempt 1
                }
                continue
            }
            if ($StopHuntStates -contains $desc.State) {
                Write-Log "SUCCESS_STOP_HUNT: $Name reached $($desc.State) in $Zone." "SUCCESS"
                Write-StopFile -Name $Name -Zone $Zone -State $desc.State
                Wait-UntilUsable -Name $Name -Zone $Zone
            }
            if ($TerminalCleanupStates -contains $desc.State) {
                Remove-CurrentAttempt -Name $Name -Zone $Zone -State $desc.State
                return
            }
            if ($ManualInspectionStates -contains $desc.State) {
                Write-Log "$Name reached $($desc.State). Refusing automatic cleanup; inspect manually." "ERROR"
                Write-StopFile -Name $Name -Zone $Zone -State $desc.State
                exit 5
            }
        } else {
            Write-Log "Attempt $Name not visible yet in $Zone."
        }
        Start-Sleep -Seconds $PollSeconds
    }

    Write-Log "Create command succeeded but $Name did not reach a known state within $CreatePollMinutes minutes. Refusing to continue to avoid duplicate unknown resources." "ERROR"
    Write-StopFile -Name $Name -Zone $Zone -State "UNKNOWN_AFTER_CREATE"
    exit 3
}

try {
    Write-Log "Script loaded. logPath=$LogPath stopFile=$StopFile"
    Run-Preflight

    if (-not $Execute) {
        Write-Log "DRY RUN ONLY. No resources were created. Re-run with -Execute to start this hunter." "WARN"
        exit 0
    }

    if ($PreflightOnly) {
        Write-Log "PreflightOnly set. Exiting before create attempts."
        exit 0
    }

    while ($true) {
        if (Test-Path -LiteralPath $StopFile) {
            Write-Log "Stop file detected before new attempt: $StopFile. Exiting."
            exit 0
        }

        foreach ($zone in ($Zones | Get-Random -Count $Zones.Count)) {
            if (Test-Path -LiteralPath $StopFile) {
                Write-Log "Stop file detected before new attempt: $StopFile. Exiting."
                exit 0
            }

            $quota = Test-QuotaForZone -Zone $zone
            if (-not $quota.Ok) {
                Write-Log "QUOTA_SKIP zone=$zone reason=$($quota.Reason). Not stockout." "WARN"
                continue
            }

            $name = New-AttemptName
            Invoke-Attempt -Name $name -Zone $zone
            Start-Sleep -Seconds 10
        }

        Write-Log "Completed sweep. Resting $SweepRestSeconds seconds before next randomized sweep."
        Start-Sleep -Seconds $SweepRestSeconds
    }
} catch {
    $message = ($_ | Out-String).Trim()
    Write-Log "FATAL_UNHANDLED_EXCEPTION: $message" "ERROR"
    exit 99
}
