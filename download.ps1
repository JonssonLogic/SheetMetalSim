<#
.SYNOPSIS
    Student installer. Downloads this project from GitHub and installs it.

.DESCRIPTION
    Fetched and run in one step from install.bat:

        powershell -Command "iex (irm https://raw.githubusercontent.com/.../download.ps1)"

    It downloads the current main branch as a zip, unpacks it to a temporary
    folder, runs install.ps1 from there, and deletes the temporary folder again.
    Nothing is left behind on the student's machine except the installed files.

    Because it is run through iex it cannot take parameters - $PSScriptRoot is
    empty in that context too, so every path here is absolute or temporary.
    Anyone who needs the options (-DryRun, -Backup, -AnsaVersion, -AnsaInstall)
    should download the repo and run install.ps1 directly.

    No administrator rights are needed: everything is written under the user's
    own profile.

    NOTE: install.bat deliberately avoids the usual "irm URL | iex" form.
    Measured 2026-09-14: Windows Defender classifies that command line as
    Trojan:Win32/Commando.A!ml, kills PowerShell, and cmd reports the exit
    code 5 as "Access is denied". "iex (irm URL)" is not flagged.
#>

$ErrorActionPreference = 'Stop'

$Owner  = 'JonssonLogic'
$Repo   = 'SheetMetalSim'
$Branch = 'main'

# Two routes to the same bytes. github.com/archive redirects to codeload, and
# when GitHub has to build the archive it can time out (a 504 was seen on
# 2026-09-14); codeload is the direct path and is tried next.
$ZipUrls = @(
    "https://github.com/$Owner/$Repo/archive/refs/heads/$Branch.zip",
    "https://codeload.github.com/$Owner/$Repo/zip/refs/heads/$Branch"
)

$Work    = Join-Path $env:TEMP ("SheetMetalSim-install-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$ZipPath = Join-Path $Work 'source.zip'

function Write-Head($text) {
    Write-Host ''
    Write-Host $text -ForegroundColor Cyan
    Write-Host ('-' * $text.Length) -ForegroundColor Cyan
}

function Get-Archive($destination) {
    <#
        One transient failure must not end the install. A whole class starting
        at once is exactly when GitHub is slowest to answer, and the first
        request is the expensive one - it builds the archive, which measured
        4.7s cold against 0.2s warm.
    #>
    $attempt = 0
    foreach ($url in $ZipUrls) {
        for ($try = 1; $try -le 3; $try++) {
            $attempt++
            try {
                Invoke-WebRequest -Uri $url -OutFile $destination -UseBasicParsing -TimeoutSec 90
                return $url
            } catch {
                Write-Host ("  [retry {0}] {1}" -f $attempt, $_.Exception.Message) -ForegroundColor Yellow
                if ($try -lt 3) { Start-Sleep -Seconds (2 * $try) }
            }
        }
    }
    throw "Could not download the project after $attempt attempts. Check that the machine can reach github.com, and that the '$Branch' branch still exists - a wrong branch name fails the same way."
}

Write-Head 'Sheet metal forming automation - download and install'
Write-Host ("  source : {0}" -f $ZipUrls[0])
Write-Host ("  temp   : {0}" -f $Work)

# ANSA and META rewrite their own configuration when they exit, so an install
# done while they are open is silently undone. install.ps1 warns about this too,
# but by then the download has already happened.
$running = @(Get-Process -Name 'ansa*', 'meta*' -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    Write-Host ''
    Write-Host '  [WARN] ANSA or META appears to be running.' -ForegroundColor Yellow
    Write-Host '         They rewrite their configuration when they close, which would' -ForegroundColor Yellow
    Write-Host '         undo this install. Close them now.' -ForegroundColor Yellow
    Write-Host ''
    Read-Host '         Press Enter once they are closed (or Ctrl+C to stop)' | Out-Null
}

try {
    New-Item -ItemType Directory -Path $Work -Force | Out-Null

    Write-Head 'Downloading'
    # The progress bar makes Invoke-WebRequest several times slower.
    $previousProgress = $ProgressPreference
    $ProgressPreference = 'SilentlyContinue'
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $used = Get-Archive $ZipPath
    } finally {
        $ProgressPreference = $previousProgress
    }
    $size = (Get-Item $ZipPath).Length / 1MB
    Write-Host ("  [OK] {0:N1} MB from {1}" -f $size, ([Uri]$used).Host) -ForegroundColor Green

    Write-Head 'Unpacking'
    Expand-Archive -Path $ZipPath -DestinationPath $Work -Force
    # GitHub names the folder inside the zip <repo>-<branch>.
    $source = Join-Path $Work "$Repo-$Branch"
    if (-not (Test-Path $source)) {
        $source = (Get-ChildItem -Path $Work -Directory | Select-Object -First 1).FullName
    }
    $installer = Join-Path $source 'install.ps1'
    if (-not (Test-Path $installer)) {
        throw "install.ps1 was not in the download. Expected it at $installer"
    }
    Write-Host ("  [OK] {0}" -f $source) -ForegroundColor Green

    & $installer
}
catch {
    Write-Host ''
    Write-Host '  [FAIL] The install did not complete.' -ForegroundColor Red
    Write-Host ("         {0}" -f $_.Exception.Message) -ForegroundColor Red
    Write-Host ''
    Write-Host '  If it says the ANSA installation was not found, ANSA 25.1.1 has to be' -ForegroundColor Yellow
    Write-Host '  installed first - this only adds the teaching macros to it.' -ForegroundColor Yellow
    Write-Host '  If it says a file could not be written, close ANSA and META and retry.' -ForegroundColor Yellow
    Write-Host '  If it could not download, wait a moment and run this again.' -ForegroundColor Yellow
    exit 1
}
finally {
    if (Test-Path $Work) {
        Remove-Item -Path $Work -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Head 'Finished'
Write-Host '  Start ANSA. The buttons appear under "Sheet metal forming",'
Write-Host '  "Spring back" and "Deformed shape".'
Write-Host ''
