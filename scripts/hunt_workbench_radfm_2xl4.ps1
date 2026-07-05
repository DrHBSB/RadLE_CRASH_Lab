[CmdletBinding()]
param(
    [string]$Project = "crashlab-synthetic",
    [string]$InstanceName = "medical-master-radfm",
    [switch]$Execute,
    [switch]$PreflightOnly,
    [int]$CreateWaitSeconds = 75,
    [int]$VerifyPollSeconds = 30,
    [int]$SweepRestSeconds = 60,
    [string]$LogPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$L4Zones = @(
    "us-central1-a", "us-central1-b", "us-central1-c",
    "us-east1-b", "us-east1-c", "us-east1-d",
    "us-east4-a", "us-east4-c",
    "us-west1-a", "us-west1-b", "us-west1-c",
    "us-west4-a", "us-west4-c",
    "northamerica-northeast1-b", "northamerica-northeast1-c",
    "northamerica-northeast2-a", "northamerica-northeast2-b",
    "europe-west1-b", "europe-west1-c",
    "europe-west2-a", "europe-west2-b",
    "europe-west3-a", "europe-west3-b",
    "europe-west4-a", "europe-west4-b", "europe-west4-c",
    "europe-west6-b", "europe-west6-c",
    "asia-east1-a", "asia-east1-b", "asia-east1-c",
    "asia-northeast1-a", "asia-northeast1-b", "asia-northeast1-c",
    "asia-northeast3-a", "asia-northeast3-b",
    "asia-south1-a", "asia-south1-b", "asia-south1-c",
    "asia-southeast1-a", "asia-southeast1-b", "asia-southeast1-c",
    "me-central2-a", "me-central2-c"
)

$A100ZonesForInspectionOnly = @(
    "us-central1-a", "us-central1-b", "us-central1-c", "us-central1-f",
    "us-east1-b", "us-west1-b", "us-west3-b", "us-west4-b",
    "europe-west4-a", "europe-west4-b",
    "asia-northeast1-a", "asia-northeast1-c",
    "asia-northeast3-a", "asia-northeast3-b",
    "asia-southeast1-a", "asia-southeast1-b", "asia-southeast1-c",
    "me-west1-a", "me-west1-c"
)

$CriticalWorkbenchNames = @("medical-master-radfm", "medical-test-l4", "medical-master-a100")
$StopHuntStates = @("PROVISIONING", "STARTING", "INITIALIZING", "STAGING", "ACTIVE")
$TerminalCleanupStates = @("STOPPING", "STOPPED", "FAILED", "ERROR")
$AllInspectionZones = @($L4Zones + $A100ZonesForInspectionOnly) | Sort-Object -Unique

if (-not $LogPath) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $LogPath = Join-Path (Get-Location) "outputs\gcp_hunt\radfm_2xl4_hunt_$stamp.log"
}
$logDir = Split-Path -Parent $LogPath
if ($logDir) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"), $Level, $Message
    Write-Host $line
    Add-Content -LiteralPath $LogPath -Value $line
}

function Invoke-Gcloud {
    param(
        [string[]]$Args,
        [switch]$AllowFailure
    )
    $output = & gcloud @Args 2>&1 | ForEach-Object { $_.ToString() }
    $code = $LASTEXITCODE
    $text = ($output -join [Environment]::NewLine).Trim()
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "gcloud $($Args -join ' ') failed with exit $code`n$text"
    }
    [pscustomobject]@{
        Code = $code
        Text = $text
    }
}

function Get-RegionFromZone {
    param([string]$Zone)
    return ($Zone -replace "-[a-z]$", "")
}

function Get-WorkbenchInstance {
    param(
        [string]$Name,
        [string]$Zone
    )
    $result = Invoke-Gcloud -Args @(
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
            Raw = $null
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
        Raw = $raw
    }
}

function Get-QuotaRows {
    param([string[]]$Regions)
    foreach ($region in ($Regions | Sort-Object -Unique)) {
        $result = Invoke-Gcloud -Args @(
            "compute", "regions", "describe", $region,
            "--project=$Project",
            "--format=json"
        ) -AllowFailure
        if ($result.Code -ne 0) {
            [pscustomobject]@{
                Region = $region
                Metric = "REGION_DESCRIBE_ERROR"
                Limit = 0.0
                Usage = 0.0
                Headroom = 0.0
                Error = $result.Text
            }
            continue
        }
        $regionJson = $result.Text | ConvertFrom-Json
        foreach ($quota in $regionJson.quotas | Where-Object { $_.metric -match "L4|A100|GPU|CPUS" }) {
            $limit = [double]$quota.limit
            $usage = [double]$quota.usage
            [pscustomobject]@{
                Region = $region
                Metric = [string]$quota.metric
                Limit = $limit
                Usage = $usage
                Headroom = ($limit - $usage)
                Error = ""
            }
        }
    }
}

function Test-L4QuotaForRegion {
    param([string]$Region)
    $rows = @(Get-QuotaRows -Regions @($Region))
    $l4 = $rows | Where-Object { $_.Metric -eq "NVIDIA_L4_GPUS" } | Select-Object -First 1
    $cpu = $rows | Where-Object { $_.Metric -eq "CPUS" } | Select-Object -First 1

    if (-not $l4) {
        return [pscustomobject]@{ Ok = $false; Reason = "No NVIDIA_L4_GPUS quota row visible in $Region"; Rows = $rows }
    }
    if ($l4.Headroom -lt 2) {
        return [pscustomobject]@{ Ok = $false; Reason = "L4 quota headroom is $($l4.Headroom), need 2"; Rows = $rows }
    }
    if ($cpu -and $cpu.Headroom -lt 24) {
        return [pscustomobject]@{ Ok = $false; Reason = "CPU quota headroom is $($cpu.Headroom), need 24 for g2-standard-24"; Rows = $rows }
    }
    return [pscustomobject]@{ Ok = $true; Reason = "Quota headroom OK"; Rows = $rows }
}

function Find-CriticalWorkbenchInstances {
    foreach ($name in $CriticalWorkbenchNames) {
        foreach ($zone in $AllInspectionZones) {
            $found = Get-WorkbenchInstance -Name $name -Zone $zone
            if ($found) {
                $found
            }
        }
    }
}

function Run-Preflight {
    Write-Log "Preflight starting for project=$Project instance=$InstanceName"

    $projectValue = (Invoke-Gcloud -Args @("config", "get-value", "project") -AllowFailure).Text
    Write-Log "gcloud active project: $projectValue"
    if ($projectValue -and $projectValue -ne $Project) {
        Write-Log "Active gcloud project differs from requested project. The script still passes --project=$Project on all resource commands." "WARN"
    }

    $auth = (Invoke-Gcloud -Args @("auth", "list", "--filter=status:ACTIVE", "--format=value(account)") -AllowFailure).Text
    Write-Log "gcloud active account: $auth"

    $services = (Invoke-Gcloud -Args @("services", "list", "--enabled", "--project=$Project", "--format=value(config.name)") -AllowFailure).Text
    foreach ($svc in @("compute.googleapis.com", "notebooks.googleapis.com", "aiplatform.googleapis.com")) {
        if ($services -notmatch [regex]::Escape($svc)) {
            Write-Log "Required API is not visible as enabled: $svc" "ERROR"
            return [pscustomobject]@{ ReadyToHunt = $false; Reason = "Missing API $svc" }
        }
    }

    $regions = $L4Zones | ForEach-Object { Get-RegionFromZone $_ } | Sort-Object -Unique
    $quotaRows = @(Get-QuotaRows -Regions $regions)
    $blocked = @($quotaRows | Where-Object {
        ($_.Metric -eq "NVIDIA_L4_GPUS" -and $_.Headroom -lt 2) -or
        ($_.Metric -eq "CPUS" -and $_.Headroom -lt 24) -or
        ($_.Metric -eq "REGION_DESCRIBE_ERROR")
    })
    foreach ($row in $blocked) {
        Write-Log ("Quota/access preflight warning: region={0} metric={1} limit={2} usage={3} headroom={4} error={5}" -f $row.Region, $row.Metric, $row.Limit, $row.Usage, $row.Headroom, $row.Error) "WARN"
    }

    $critical = @(Find-CriticalWorkbenchInstances)
    if ($critical.Count -gt 0) {
        foreach ($item in $critical) {
            Write-Log ("Existing critical Workbench resource found: name={0} zone={1} state={2} proxyUri={3} error={4}" -f $item.Name, $item.Zone, $item.State, $item.ProxyUri, $item.Error) "WARN"
        }
        return [pscustomobject]@{
            ReadyToHunt = $false
            Reason = "Existing critical Workbench resource found. Inspect value before creating or deleting anything."
            ExistingCritical = $critical
        }
    }

    return [pscustomobject]@{ ReadyToHunt = $true; Reason = "Preflight passed"; ExistingCritical = @() }
}

function Wait-WorkbenchUsable {
    param(
        [string]$Zone
    )
    Write-Log "Hunt stopped. Verifying $InstanceName in $Zone until ACTIVE with proxyUri."
    while ($true) {
        $desc = Get-WorkbenchInstance -Name $InstanceName -Zone $Zone
        if (-not $desc) {
            Write-Log "$InstanceName disappeared from $Zone during verification." "ERROR"
            exit 4
        }
        Write-Log ("Verification state: zone={0} state={1} proxyUri={2}" -f $Zone, $desc.State, $desc.ProxyUri)
        if ($desc.State -eq "ACTIVE" -and $desc.ProxyUri) {
            Write-Log "USABLE: $InstanceName is ACTIVE in $Zone with proxyUri=$($desc.ProxyUri)" "SUCCESS"
            exit 0
        }
        if ($TerminalCleanupStates -contains $desc.State) {
            Write-Log "The instance reached terminal state $($desc.State) after the hunt stopped. Manual inspection required before any restart." "ERROR"
            exit 5
        }
        Start-Sleep -Seconds $VerifyPollSeconds
    }
}

function Try-DeleteCurrentFailedAttempt {
    param(
        [string]$Zone,
        [string]$State
    )
    Write-Log "Deleting current failed attempt only: $InstanceName in $Zone state=$State"
    $delete = Invoke-Gcloud -Args @(
        "workbench", "instances", "delete", $InstanceName,
        "--location=$Zone",
        "--project=$Project",
        "--quiet"
    ) -AllowFailure
    if ($delete.Code -eq 0) {
        Write-Log "Deleted failed current attempt in $Zone."
    } else {
        Write-Log "Delete attempt returned exit $($delete.Code): $($delete.Text)" "WARN"
    }
}

Write-Log "Script loaded. LogPath=$LogPath"
if (-not $Execute) {
    if (-not $PreflightOnly) {
        Write-Log "DRY RUN: no resources will be created. Use -PreflightOnly for checks or -Execute to start the Workbench hunt." "WARN"
    }
    $preflight = Run-Preflight
    Write-Log "Preflight result: ReadyToHunt=$($preflight.ReadyToHunt) Reason=$($preflight.Reason)"
    exit 0
}

$preflightResult = Run-Preflight
if (-not $preflightResult.ReadyToHunt) {
    Write-Log "Refusing to start hunt: $($preflightResult.Reason)" "ERROR"
    exit 2
}

Write-Log "EXECUTE mode: starting Workbench 2x L4 hunt for $InstanceName. Shape=g2-standard-24, NVIDIA_L4 x2, 200GB PD_BALANCED."

while ($true) {
    $attemptZones = $L4Zones | Get-Random -Count $L4Zones.Count
    foreach ($zone in $attemptZones) {
        $region = Get-RegionFromZone $zone
        $quotaCheck = Test-L4QuotaForRegion -Region $region
        if (-not $quotaCheck.Ok) {
            Write-Log "QUOTA_SKIP zone=$zone region=$region reason=$($quotaCheck.Reason). This is not a stockout." "WARN"
            continue
        }

        Write-Log "Trying 2x L4 Workbench in $zone..."
        $create = Invoke-Gcloud -Args @(
            "workbench", "instances", "create", $InstanceName,
            "--location=$zone",
            "--project=$Project",
            "--machine-type=g2-standard-24",
            "--accelerator-type=NVIDIA_L4",
            "--accelerator-core-count=2",
            "--boot-disk-size=200",
            "--boot-disk-type=PD_BALANCED",
            "--install-gpu-driver",
            "--labels=radle-hunt=radfm,managed-by=codex",
            "--async"
        ) -AllowFailure

        if ($create.Text) {
            Write-Log "Create output: $($create.Text)"
        }

        if ($create.Code -ne 0) {
            $afterFailure = Get-WorkbenchInstance -Name $InstanceName -Zone $zone
            if ($afterFailure -and ($StopHuntStates -contains $afterFailure.State)) {
                Write-Log "Create returned nonzero, but instance exists in stop-hunt state $($afterFailure.State). Stopping hunt."
                Wait-WorkbenchUsable -Zone $zone
            }
            if ($create.Text -match "quota|QUOTA|Insufficient regional quota|exceeded") {
                Write-Log "QUOTA_FAILURE zone=$zone. Do not classify this as stockout." "WARN"
            } elseif ($create.Text -match "resource.*exhausted|stockout|currently unavailable|does not have enough resources|ZONE_RESOURCE_POOL_EXHAUSTED") {
                Write-Log "STOCKOUT_CREATE_FAILURE zone=$zone." "WARN"
            } elseif ($create.Text -match "LOCATION_POLICY|PERMISSION_DENIED|not supported") {
                Write-Log "ACCESS_OR_SUPPORT_SKIP zone=$zone. Not a stockout." "WARN"
            } else {
                Write-Log "CREATE_ERROR zone=$zone exit=$($create.Code). Manual review may be needed." "ERROR"
            }
            continue
        }

        Start-Sleep -Seconds $CreateWaitSeconds
        $desc = Get-WorkbenchInstance -Name $InstanceName -Zone $zone
        if (-not $desc) {
            Write-Log "No instance visible after create wait in $zone. Continuing without cleanup because there is no exact resource to delete." "WARN"
            continue
        }

        Write-Log ("Post-create state: zone={0} state={1} proxyUri={2}" -f $zone, $desc.State, $desc.ProxyUri)

        if ($StopHuntStates -contains $desc.State) {
            Write-Log "SUCCESS_STOP_HUNT: $InstanceName reached $($desc.State) in $zone. Stop other hunts now." "SUCCESS"
            Wait-WorkbenchUsable -Zone $zone
        }

        if ($TerminalCleanupStates -contains $desc.State) {
            Write-Log "FAILED_ATTEMPT: $InstanceName reached $($desc.State) in $zone. Cleaning only this current failed attempt." "WARN"
            Try-DeleteCurrentFailedAttempt -Zone $zone -State $desc.State
            continue
        }

        Write-Log "UNKNOWN_STATE zone=$zone state=$($desc.State). Refusing to continue or delete. Inspect manually." "ERROR"
        exit 3
    }

    Write-Log "Completed randomized sweep. Resting $SweepRestSeconds seconds before next sweep."
    Start-Sleep -Seconds $SweepRestSeconds
}
