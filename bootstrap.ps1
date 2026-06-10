<#
================================================================================
 Goodtrade AMS - fresh-machine bootstrap
================================================================================
 Purpose: take a bare Windows box (nothing installed but Ppro + PowerShell) and
 get Goodtrade AMS fully set up and launchable, with ZERO manual steps.

 It is IDEMPOTENT: safe to run again. Each step checks whether it's already done
 and skips it. So you can also use this to "repair" a half-broken install.

 What it does, in order:
   1. Ensure Git is installed            (winget, else bundled/Downloaded installer)
   2. Ensure Python 3.12 is installed    (uses install\python-3.12.10-amd64.exe if present)
   3. Ensure the repo is cloned          (git clone, or reuse if already here)
   4. Install pinned deps                 (python -m pip install -r requirements.lock)
   5. Hand off to "Goodtrade AMS.cmd"     (your normal launcher / auto-updater)

 USAGE
 -----
 On a fresh machine, open PowerShell and run ONE of:

   # If you already copied this file onto the machine:
   powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1

   # Or one-liner straight from GitHub (raw URL of this file):
   irm https://raw.githubusercontent.com/chiaochiaoo/Goodtrade2/main/bootstrap.ps1 | iex

 Optional switches:
   -RepoDir   <path>   Where to clone/find the repo   (default: C:\Goodtrade2)
   -NoLaunch           Set everything up but don't start the app at the end
   -Branch    <name>   Branch to clone                (default: main)

 NOTE: This script needs INTERNET at setup time (to fetch Git / Python / pip
 packages). That's a one-time cost. After setup, the normal launcher only needs
 internet for its git auto-update, and can be hardened to run offline.
================================================================================
#>

[CmdletBinding()]
param(
    [string]$RepoDir = 'C:\Goodtrade2',
    [string]$Branch  = 'main',
    [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
$RepoUrl   = 'https://github.com/chiaochiaoo/Goodtrade2.git'
$PyVersion = '3.12'
$PyInstallerName = 'python-3.12.10-amd64.exe'   # the one you already bundle in install\

# --- pretty logging -----------------------------------------------------------
function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    [ok] $msg"   -ForegroundColor Green }
function Info($msg) { Write-Host "    $msg"        -ForegroundColor Gray }
function Warn($msg) { Write-Host "    [warn] $msg" -ForegroundColor Yellow }
function Die($msg)  { Write-Host "`n[FATAL] $msg" -ForegroundColor Red; Read-Host 'Press Enter to exit'; exit 1 }

# Re-find a command after an installer adds it to PATH (the current shell won't
# see PATH changes until we refresh it from the machine + user environment).
function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path','Machine')
    $user    = [Environment]::GetEnvironmentVariable('Path','User')
    $env:Path = ($machine, $user | Where-Object { $_ }) -join ';'
}

function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

Write-Host "================================================" -ForegroundColor White
Write-Host " Goodtrade AMS bootstrap" -ForegroundColor White
Write-Host " Target dir : $RepoDir" -ForegroundColor White
Write-Host " Branch     : $Branch"  -ForegroundColor White
Write-Host "================================================" -ForegroundColor White

# Where does THIS script live? If we were run from inside an existing checkout,
# we can reuse the bundled Python installer and the repo itself.
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }

# ------------------------------------------------------------------------------
# 1. GIT
# ------------------------------------------------------------------------------
Step 'Checking for Git'
if (Have 'git') {
    Ok "Git already installed ($((git --version)))"
} else {
    Info 'Git not found - installing...'
    $installed = $false

    # Preferred: winget (present on Win10 21H2+ / Win11). Cleanest, no manual download.
    if (Have 'winget') {
        Info 'Installing Git via winget...'
        # --silent: no UI; accept agreements so it doesn't block on a prompt.
        winget install --id Git.Git -e --silent `
            --accept-package-agreements --accept-source-agreements
        Refresh-Path
        if (Have 'git') { $installed = $true }
    }

    # Fallback: download the official installer and run it silently.
    if (-not $installed) {
        Warn 'winget unavailable or failed; downloading Git installer directly...'
        $gitExe = Join-Path $env:TEMP 'git-installer.exe'
        # Stable "latest 64-bit" redirect from the Git for Windows project.
        $gitUrl = 'https://github.com/git-for-windows/git/releases/latest/download/Git-64-bit.exe'
        try {
            Info "Downloading $gitUrl ..."
            Invoke-WebRequest -Uri $gitUrl -OutFile $gitExe -UseBasicParsing
            # /VERYSILENT /NORESTART = unattended; /NOICONS skips start-menu clutter.
            Info 'Running Git installer silently...'
            Start-Process -FilePath $gitExe -ArgumentList '/VERYSILENT','/NORESTART','/NOICONS' -Wait
            Refresh-Path
            if (Have 'git') { $installed = $true }
        } catch {
            Die "Could not download/install Git automatically: $($_.Exception.Message)`n    Install Git manually from https://git-scm.com/download/win then re-run this script."
        }
    }

    if ($installed) { Ok "Git installed ($((git --version)))" }
    else { Die 'Git still not on PATH after install. Open a NEW PowerShell window and re-run this script.' }
}

# ------------------------------------------------------------------------------
# 2. PYTHON 3.12
# ------------------------------------------------------------------------------
Step "Checking for Python $PyVersion"

# Resolve a python.exe that is actually 3.12. The Windows `py` launcher is the
# most reliable way to ask for a specific version if multiple are installed.
function Get-Python312 {
    # Print "major.minor" with no quotes in the Python source, so nothing needs
    # escaping when the one-liner is passed through PowerShell.
    $probe = 'import sys;print(str(sys.version_info[0])+chr(46)+str(sys.version_info[1]))'
    if (Have 'py') {
        try {
            $v = (& py "-$PyVersion" -c $probe 2>$null) | Select-Object -First 1
            if ("$v".Trim() -eq $PyVersion) { return @('py', "-$PyVersion") }
        } catch {}
    }
    if (Have 'python') {
        try {
            $v = (& python -c $probe 2>$null) | Select-Object -First 1
            if ("$v".Trim() -eq $PyVersion) { return @('python') }
        } catch {}
    }
    return $null
}

$PyCmd = Get-Python312
if ($PyCmd) {
    Ok "Python $PyVersion already installed"
} else {
    Info "Python $PyVersion not found - installing..."

    # Prefer the installer you already bundle in the repo's install\ folder.
    $bundled = @(
        (Join-Path $ScriptDir "install\$PyInstallerName"),
        (Join-Path $RepoDir  "install\$PyInstallerName")
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    $pyExe = $null
    if ($bundled) {
        Info "Using bundled installer: $bundled"
        $pyExe = $bundled
    } else {
        Warn 'Bundled Python installer not found locally; downloading from python.org...'
        $pyExe = Join-Path $env:TEMP $PyInstallerName
        $pyUrl = "https://www.python.org/ftp/python/3.12.10/$PyInstallerName"
        try {
            Info "Downloading $pyUrl ..."
            Invoke-WebRequest -Uri $pyUrl -OutFile $pyExe -UseBasicParsing
        } catch {
            Die "Could not download Python: $($_.Exception.Message)`n    Install Python 3.12 manually (check 'Add to PATH') then re-run."
        }
    }

    # Silent, all-users install, add to PATH, include the py launcher.
    # NOTE: do NOT name this $args - that's a PowerShell automatic variable and
    # collides badly when the script is run through `iex`.
    Info 'Running Python installer silently (this can take a minute)...'
    $pyInstallArgs = @(
        '/quiet',
        'InstallAllUsers=1',
        'PrependPath=1',
        'Include_launcher=1',
        'Include_test=0'
    )
    Start-Process -FilePath $pyExe -ArgumentList $pyInstallArgs -Wait
    Refresh-Path

    $PyCmd = Get-Python312
    if (-not $PyCmd) {
        Die "Python $PyVersion still not detected after install. Open a NEW PowerShell window and re-run this script."
    }
    Ok "Python $PyVersion installed"
}

# Build the python invocation (handles the `py -3.12` case). We keep the exe and
# its leading args as an array and ALWAYS call via `& $PyExe @PyPrefix <more args>`
# with a fully-built argument array. This is important: when this whole script is
# run through `irm ... | iex`, splatting user-style params (e.g. -m) through a
# helper function makes PowerShell try to bind `-m` to `iex` itself and fail.
# Passing a flat array to the native exe avoids that entirely.
$PyExe    = $PyCmd[0]
$PyPrefix = @($PyCmd[1..($PyCmd.Length-1)])   # empty unless it's `py -3.12`

function Invoke-Py {
    # Takes a SINGLE array of arguments and forwards it to python. Callers build
    # the array explicitly (no PowerShell param parsing on the python flags).
    param([string[]]$PyArgList)
    & $PyExe @PyPrefix @PyArgList
}

# ------------------------------------------------------------------------------
# 3. REPO
# ------------------------------------------------------------------------------
Step "Ensuring repo is present at $RepoDir"

if (Test-Path (Join-Path $RepoDir '.git')) {
    Ok 'Repo already cloned'
    Info 'Fetching latest...'
    git -C $RepoDir fetch origin
    git -C $RepoDir checkout $Branch
    git -C $RepoDir reset --hard "origin/$Branch"
    Ok "Updated to latest origin/$Branch"
}
elseif ((Test-Path $RepoDir) -and (Get-ChildItem $RepoDir -Force | Measure-Object).Count -gt 0) {
    # Folder exists with files but isn't a git repo. Most likely: this script was
    # copied in alongside the code without it being a clone. Don't clobber it.
    Warn "$RepoDir exists and is not empty but is not a git repo."
    Warn 'Skipping clone to avoid destroying files. If you want git auto-update,'
    Warn 'back up this folder, delete it, and re-run so it can be cloned cleanly.'
}
else {
    Info "Cloning $RepoUrl ..."
    git clone --branch $Branch $RepoUrl $RepoDir
    Ok 'Repo cloned'
}

# ------------------------------------------------------------------------------
# 4. PYTHON DEPENDENCIES (pinned)
# ------------------------------------------------------------------------------
Step 'Installing Python dependencies (pinned)'

$lock = Join-Path $RepoDir 'requirements.lock'
Info 'Upgrading pip...'
Invoke-Py @('-m','pip','install','--upgrade','pip','--quiet')

if (Test-Path $lock) {
    Info "Installing from requirements.lock ..."
    Invoke-Py @('-m','pip','install','-r',$lock)
    Ok 'Pinned dependencies installed'
} else {
    Warn 'requirements.lock not found - falling back to unpinned core deps.'
    Warn '(Pull the latest repo so requirements.lock is present for reproducible installs.)'
    Invoke-Py @('-m','pip','install',
        'ttkbootstrap==1.13.10','matplotlib','numpy','pandas','requests',
        'psutil','flask','firebase-admin','pytz','pymongo','psycopg2-binary','redis')
    Ok 'Core dependencies installed (unpinned fallback)'
}

# ------------------------------------------------------------------------------
# 5. DONE / LAUNCH
# ------------------------------------------------------------------------------
Step 'Setup complete'
Ok "Goodtrade AMS is installed at $RepoDir"

if ($NoLaunch) {
    Info 'Skipping launch (-NoLaunch). To start it yourself, run:'
    Info "    cd `"$RepoDir`"  ;  .\`"Goodtrade AMS.cmd`""
    Write-Host ''
    exit 0
}

$launcher = Join-Path $RepoDir 'Goodtrade AMS.cmd'
if (Test-Path $launcher) {
    Info 'Launching Goodtrade AMS...'
    Info '(reminder: Ppro must be running on this machine for the app to connect)'
    Push-Location $RepoDir
    & cmd.exe /c "`"$launcher`""
    Pop-Location
} else {
    Warn "Launcher not found at: $launcher"
    Warn 'Setup is done, but I could not find the .cmd to start it.'
}

Write-Host "`nAll done.`n" -ForegroundColor Green
