<#
.SYNOPSIS
    Student installer. Downloads this project from GitHub and installs it.

.DESCRIPTION
    Fetched and run in one step from install.bat:

        irm https://raw.githubusercontent.com/JonssonLogic/SheetMetalSim/main/download.ps1 | iex

    It downloads the current main branch as a zip, unpacks it to a temporary
    folder, runs install.ps1 from there, and deletes the temporary folder again.
    Nothing is left behind on the student's machine except the installed files.

    Because it is run through iex it cannot take parameters - $PSScriptRoot is
    empty in that context too, so every path here is absolute or temporary.
    Anyone who needs the options (-DryRun, -Backup, -AnsaVersion, -AnsaInstall)
    should download the repo and run install.ps1 directly.

    No administrator rights are needed: everything is written under the user's
    own profile.
#>

$ErrorActionPreference = 'Stop'

$Owner  = 'JonssonLogic'
$Repo   = 'SheetMetalSim'
$Branch = 'main'

$ZipUrl  = "https://github.com/$Owner/$Repo/archive/refs/heads/$Branch.zip"
$Work    = Join-Path $env:TEMP ("SheetMetalSim-install-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$ZipPath = Join-Path $Work 'source.zip'

function Write-Head($text) {
    Write-Host ''
    Write-Host $text -ForegroundColor Cyan
    Write-Host ('-' * $text.Length) -ForegroundColor Cyan
}

Write-Head 'Sheet metal forming automation - download and install'
Write-Host ("  source : {0}" -f $ZipUrl)
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
        Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath -UseBasicParsing
    } finally {
        $ProgressPreference = $previousProgress
    }
    $size = (Get-Item $ZipPath).Length / 1MB
    Write-Host ("  [OK] {0:N1} MB" -f $size) -ForegroundColor Green

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
