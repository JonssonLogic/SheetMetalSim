<#
.SYNOPSIS
    Installs the sheet metal forming automation into a local ANSA / META installation.

.DESCRIPTION
    Pure file copying. It mirrors this project folder into the two places ANSA and
    META actually read from:

        Ansa\3D-teknik\        ->  <BetaHome>\ANSA\version_<V>\3D-teknik\
        Ansa\Translators\      ->  <BetaHome>\Translators\
        Ansa\ANSA_TRANSL.py    ->  <AnsaInstall>\ansa_v<V>\config\
        Ansa\ANSA.xml          ->  <BetaHome>\ANSA\version_<V>\
        Ansa\ANSA.defaults     ->  <BetaHome>\ANSA\version_<V>\
        Ansa\launcher.txt      ->  <BetaHome>\ANSA\version_<V>\
        explicit-main.k        ->  <BetaHome>\ANSA\version_<V>\3D-teknik\
        implicit-main.k        ->  <BetaHome>\ANSA\version_<V>\3D-teknik\
        forming_materials.k    ->  <BetaHome>\ANSA\version_<V>\3D-teknik\
        Meta\3D-teknik\        ->  <BetaHome>\META\version_<V>\3D-teknik\
        Meta\default\          ->  <BetaHome>\META\version_<V>\default\

    The three .k files are templates the scripts read at run time: the export
    steps copy a deck next to the exported model and patch it, and the import
    materials step reads forming_materials.k without asking. They are deployed
    into 3D-teknik alongside the scripts that read them.

    Existing files are overwritten.

.PARAMETER AnsaVersion
    ANSA / META version, as it appears in the folder names. Default 25.1.1,
    which produces "version_25.1.1" and "ansa_v25.1.1".

.PARAMETER BetaHome
    The .BETA folder. Defaults to $env:USERPROFILE\.BETA.

.PARAMETER AnsaInstall
    Folder holding ansa_v<version>. Defaults to
    $env:LOCALAPPDATA\Apps\BETA_CAE_Systems.

.PARAMETER DryRun
    Report what would be copied and change nothing.

.PARAMETER Backup
    Before overwriting, copy the existing target into a timestamped folder
    next to it. Recommended the first time you run this on a machine that
    already has a working setup.

.EXAMPLE
    .\install.ps1 -DryRun
    Show what would happen.

.EXAMPLE
    .\install.ps1 -Backup
    Install, keeping a copy of whatever is replaced.

.NOTES
    Close ANSA and META before running. Both rewrite ANSA.xml / ANSA.defaults
    and their META equivalents when they exit, which would silently undo an
    install performed while they were open.
#>
[CmdletBinding()]
param(
    [string]$AnsaVersion = '25.1.1',
    [string]$BetaHome    = (Join-Path $env:USERPROFILE '.BETA'),
    [string]$AnsaInstall = (Join-Path $env:LOCALAPPDATA 'Apps\BETA_CAE_Systems'),
    [switch]$DryRun,
    [switch]$Backup
)

$ErrorActionPreference = 'Stop'

$SourceRoot   = $PSScriptRoot
$VersionDir   = "version_$AnsaVersion"
$AnsaAppDir   = "ansa_v$AnsaVersion"

$AnsaConfig   = Join-Path (Join-Path $AnsaInstall $AnsaAppDir) 'config'
$AnsaUserDir  = Join-Path (Join-Path $BetaHome 'ANSA') $VersionDir
$MetaUserDir  = Join-Path (Join-Path $BetaHome 'META') $VersionDir

# Source, Target, IsDirectory. Target is the containing folder for files,
# and the destination folder itself for directories.
$Plan = @(
    @{ Src = 'Ansa\3D-teknik';     Dst = (Join-Path $AnsaUserDir '3D-teknik');  Dir = $true  }
    @{ Src = 'Ansa\Translators';   Dst = (Join-Path $BetaHome 'Translators');   Dir = $true  }
    @{ Src = 'Ansa\ANSA_TRANSL.py';Dst = $AnsaConfig;                           Dir = $false }
    @{ Src = 'Ansa\ANSA.xml';      Dst = $AnsaUserDir;                          Dir = $false }
    @{ Src = 'Ansa\ANSA.defaults'; Dst = $AnsaUserDir;                          Dir = $false }
    @{ Src = 'Ansa\launcher.txt';  Dst = $AnsaUserDir;                          Dir = $false }
    # The master decks and the materials file live beside the scripts, because
    # the scripts read them: step 7 copies explicit-main.k next to the exported
    # model and patches its solve settings, springback step 3 does the same with
    # implicit-main.k, and step 3 imports forming_materials.k without asking.
    # They stay at the repo root so the docs and make_deck_variants.py keep
    # their paths; only the deployed copy moves.
    @{ Src = 'explicit-main.k';    Dst = (Join-Path $AnsaUserDir '3D-teknik');  Dir = $false }
    @{ Src = 'implicit-main.k';    Dst = (Join-Path $AnsaUserDir '3D-teknik');  Dir = $false }
    @{ Src = 'forming_materials.k';Dst = (Join-Path $AnsaUserDir '3D-teknik');  Dir = $false }
    @{ Src = 'Meta\3D-teknik';     Dst = (Join-Path $MetaUserDir '3D-teknik');  Dir = $true  }
    @{ Src = 'Meta\default';       Dst = (Join-Path $MetaUserDir 'default');    Dir = $true  }
)

function Write-Head($text) {
    Write-Host ''
    Write-Host $text -ForegroundColor Cyan
    Write-Host ('-' * $text.Length) -ForegroundColor Cyan
}

Write-Head 'Sheet metal forming automation - install'
Write-Host ("  version      : {0}" -f $AnsaVersion)
Write-Host ("  source       : {0}" -f $SourceRoot)
Write-Host ("  ANSA user dir: {0}" -f $AnsaUserDir)
Write-Host ("  ANSA config  : {0}" -f $AnsaConfig)
Write-Host ("  META user dir: {0}" -f $MetaUserDir)
if ($DryRun) { Write-Host '  MODE         : DRY RUN - nothing will be written' -ForegroundColor Yellow }

# ---- pre-flight -------------------------------------------------------------
Write-Head 'Checking'

$problems = @()

foreach ($item in $Plan) {
    $full = Join-Path $SourceRoot $item.Src
    if (-not (Test-Path $full)) {
        $problems += "missing in project: $($item.Src)"
    }
}

if (-not (Test-Path $AnsaConfig)) {
    $problems += "ANSA install not found: $AnsaConfig  (wrong -AnsaVersion or -AnsaInstall?)"
}

if ($problems.Count -gt 0) {
    foreach ($p in $problems) { Write-Host "  [FAIL] $p" -ForegroundColor Red }
    Write-Host ''
    throw 'Pre-flight checks failed. Nothing was copied.'
}
Write-Host '  [OK] all sources present, ANSA installation found' -ForegroundColor Green

$ansaRunning = @(Get-Process -Name 'ansa*','meta*' -ErrorAction SilentlyContinue)
if ($ansaRunning.Count -gt 0) {
    Write-Host '  [WARN] ANSA or META appears to be running.' -ForegroundColor Yellow
    Write-Host '         They rewrite their config on exit and will undo this install.' -ForegroundColor Yellow
}

# ---- copy -------------------------------------------------------------------
Write-Head 'Installing'

$stamp    = Get-Date -Format 'yyyyMMdd-HHmmss'
$copied   = 0

foreach ($item in $Plan) {
    $src = Join-Path $SourceRoot $item.Src

    if ($item.Dir) {
        $dstShown = $item.Dst
        $parent   = Split-Path $item.Dst -Parent
    } else {
        $dstShown = Join-Path $item.Dst (Split-Path $src -Leaf)
        $parent   = $item.Dst
    }

    if ($Backup -and -not $DryRun -and (Test-Path $dstShown)) {
        $bak = "$dstShown.bak-$stamp"
        Copy-Item -Path $dstShown -Destination $bak -Recurse -Force
        Write-Host ("  [BAK] {0}" -f $bak) -ForegroundColor DarkGray
    }

    if ($DryRun) {
        Write-Host ("  [DRY] {0,-22} -> {1}" -f $item.Src, $dstShown)
        $copied++
        continue
    }

    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    if ($item.Dir) {
        if (-not (Test-Path $item.Dst)) {
            New-Item -ItemType Directory -Path $item.Dst -Force | Out-Null
        }
        # Copy contents, not the folder itself, so repeat runs do not nest.
        Copy-Item -Path (Join-Path $src '*') -Destination $item.Dst -Recurse -Force
    } else {
        Copy-Item -Path $src -Destination $item.Dst -Force
    }

    Write-Host ("  [OK]  {0,-22} -> {1}" -f $item.Src, $dstShown) -ForegroundColor Green
    $copied++
}

# ---- verify -----------------------------------------------------------------
if (-not $DryRun) {
    Write-Head 'Verifying'
    $bad = 0
    foreach ($item in $Plan) {
        $src = Join-Path $SourceRoot $item.Src
        if ($item.Dir) {
            $srcFiles = Get-ChildItem -Path $src -Recurse -File
            foreach ($f in $srcFiles) {
                $rel = $f.FullName.Substring($src.Length).TrimStart('\')
                $tgt = Join-Path $item.Dst $rel
                if (-not (Test-Path $tgt)) {
                    Write-Host ("  [FAIL] not copied: {0}" -f $rel) -ForegroundColor Red
                    $bad++
                } elseif ((Get-FileHash $f.FullName).Hash -ne (Get-FileHash $tgt).Hash) {
                    Write-Host ("  [FAIL] differs: {0}" -f $rel) -ForegroundColor Red
                    $bad++
                }
            }
        } else {
            $tgt = Join-Path $item.Dst (Split-Path $src -Leaf)
            if (-not (Test-Path $tgt)) {
                Write-Host ("  [FAIL] not copied: {0}" -f $item.Src) -ForegroundColor Red
                $bad++
            } elseif ((Get-FileHash $src).Hash -ne (Get-FileHash $tgt).Hash) {
                Write-Host ("  [FAIL] differs: {0}" -f $item.Src) -ForegroundColor Red
                $bad++
            }
        }
    }
    if ($bad -eq 0) {
        Write-Host '  [OK] every file matches its source' -ForegroundColor Green
    } else {
        throw "$bad file(s) did not install correctly."
    }
}

Write-Head 'Done'
Write-Host ("  {0} item(s) processed." -f $copied)
if ($DryRun) {
    Write-Host '  Dry run - re-run without -DryRun to apply.' -ForegroundColor Yellow
} else {
    Write-Host '  Restart ANSA to pick up ANSA_TRANSL.py button changes.'
    Write-Host '  Scripts under 3D-teknik reload on every button click - no restart needed.'
}
Write-Host ''
