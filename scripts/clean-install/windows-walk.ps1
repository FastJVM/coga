# Windows-side half of the Windows clean-install harness. aws-windows.sh copies
# this file to C:\coga-clean-install\ on the EC2 instance and runs it over SSH
# with powershell.exe -File, so its exit code reaches the host. Keep it to the
# stock Windows PowerShell 5.1 and to ASCII (5.1 reads BOM-less files as ANSI).
# See the coga/testing/clean-install/windows-aws topic.
param(
    [Parameter(Position = 0)][string]$Mode,
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)][string[]]$Rest
)
Set-StrictMode -Version 2.0
if ($null -eq $Rest) { $Rest = @() }
# Native commands write progress to stderr; judge them by exit code, not by
# PowerShell's error stream.
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

function Fail([string]$Message, [int]$Code = 1) {
    [Console]::Error.WriteLine($Message)
    exit $Code
}

function Add-UserPath([string]$Dir) {
    if (($env:Path -split ';') -notcontains $Dir) { $env:Path = "$Dir;$env:Path" }
}

function Refresh-MachinePath {
    # Installers update the registry; this process keeps its old PATH.
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user"
}

function Install-Uv {
    # The official installer, as uv's docs give it for Windows.
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -Command 'irm https://astral.sh/uv/install.ps1 | iex'
    Add-UserPath (Join-Path $HOME '.local\bin')
}

function Show-Command([string]$Name) {
    $found = @(Get-Command $Name -All -ErrorAction SilentlyContinue)
    if ($found.Count -eq 0) { "${Name}: not on PATH" } else { $found | ForEach-Object { "${Name}: $($_.Source)" } }
}

switch ($Mode) {
    'baseline' {
        # What the box has, recorded before and after setup.
        $nt = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
        "OS: $($nt.ProductName) $($nt.DisplayVersion) build $($nt.CurrentBuild).$($nt.UBR)"
        "PowerShell: $($PSVersionTable.PSVersion)"
        "User: $(whoami)"
        Show-Command git
        if (Get-Command git -ErrorAction SilentlyContinue) { & git --version; "core.autocrlf (system): $(& git config --system core.autocrlf)" }
        Show-Command python
        Show-Command py
        Show-Command uv
        if (Get-Command python -ErrorAction SilentlyContinue) { & python --version 2>&1 | ForEach-Object { "$_" } }
        $sshd = Get-Service sshd -ErrorAction SilentlyContinue
        if ($sshd) { "sshd: $($sshd.Status), $($sshd.StartType)" }
        exit 0
    }
    'setup' {
        # Run once as Administrator by provision: Git for Windows machine-wide
        # with its installer defaults, then uv and Python 3.11 for this account
        # (the fix loop's). uv tool installs are per user, so walk users never
        # see them.
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
            $release = Invoke-RestMethod -UseBasicParsing 'https://api.github.com/repos/git-for-windows/git/releases/latest'
            $asset = @($release.assets | Where-Object { $_.name -match '^Git-[0-9.]+-64-bit\.exe$' })[0]
            if (-not $asset) { Fail "No 64-bit Git installer in $($release.tag_name)" }
            $installer = Join-Path $env:TEMP $asset.name
            "Downloading $($asset.browser_download_url)"
            Invoke-WebRequest -UseBasicParsing $asset.browser_download_url -OutFile $installer
            (Get-FileHash -Algorithm SHA256 $installer).Hash
            $proc = Start-Process -FilePath $installer -Wait -PassThru `
                -ArgumentList '/VERYSILENT', '/NORESTART', '/NOCANCEL', '/SP-', '/SUPPRESSMSGBOXES'
            if ($proc.ExitCode -ne 0) { Fail "Git installer exited $($proc.ExitCode)" $proc.ExitCode }
            Remove-Item $installer
            Refresh-MachinePath
        }
        & git --version
        if ($LASTEXITCODE -ne 0) { Fail 'git is not usable after install' }
        Install-Uv
        & uv --version
        if ($LASTEXITCODE -ne 0) { Fail 'uv install failed' }
        # --default also puts python.exe on this account's PATH for the fix loop.
        & uv python install 3.11 --default
        if ($LASTEXITCODE -ne 0) { Fail 'uv python install 3.11 failed' $LASTEXITCODE }
        exit 0
    }
    'adduser' {
        # Run as Administrator. The password comes on stdin so it never sits
        # in a process command line or the host trace.
        if ($Rest.Count -ne 1) { Fail 'usage: windows-walk.ps1 adduser USER  (password on stdin)' 2 }
        $user = $Rest[0]
        if (Get-LocalUser -Name $user -ErrorAction SilentlyContinue) {
            Fail "Local user $user already exists; choose a new name for a fresh profile" 2
        }
        $plain = [Console]::In.ReadLine()
        if (-not $plain) { Fail 'No password on stdin' 2 }
        $secure = ConvertTo-SecureString $plain -AsPlainText -Force
        New-LocalUser -Name $user -Password $secure -FullName "Coga clean install $user" `
            -PasswordNeverExpires -ErrorAction Stop | Out-Null
        # Users, plus Remote Desktop Users for RDP. Windows' default
        # sshd_config says AllowGroups administrators "openssh users", so a
        # new user needs OpenSSH Users (created with the OpenSSH capability).
        Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user -ErrorAction Stop
        Add-LocalGroupMember -SID 'S-1-5-32-555' -Member $user -ErrorAction Stop
        Add-LocalGroupMember -Group 'OpenSSH Users' -Member $user -ErrorAction Stop
        "Created local user $user"
        exit 0
    }
    'checkout' {
        # The fix loop's checkout, as Administrator in its own work directory.
        if ($Rest.Count -ne 2) { Fail 'usage: windows-walk.ps1 checkout REF REPO_URL' 2 }
        $ref = $Rest[0]
        $url = $Rest[1]
        $work = Join-Path $HOME 'coga-work'
        Add-UserPath (Join-Path $HOME '.local\bin')
        if (-not (Test-Path (Join-Path $work '.git'))) {
            & git clone $url $work
            if ($LASTEXITCODE -ne 0) { Fail 'git clone failed' $LASTEXITCODE }
        }
        Set-Location $work
        $dirty = & git status --porcelain --untracked-files=all
        if ($dirty) { Fail "Uncommitted changes in ${work}; commit them on the host or clean the box checkout first" 2 }
        # A branch name or a full SHA; GitHub serves both to fetch.
        & git fetch origin $ref
        if ($LASTEXITCODE -ne 0) { Fail "git fetch origin $ref failed" $LASTEXITCODE }
        & git checkout --detach FETCH_HEAD
        if ($LASTEXITCODE -ne 0) { Fail 'git checkout failed' $LASTEXITCODE }
        & git log -1 --format='HEAD %H %s'
        & uv sync --python 3.11 --extra test
        if ($LASTEXITCODE -ne 0) { Fail 'uv sync --extra test failed' $LASTEXITCODE }
        "Checked out $ref in $work"
        exit 0
    }
    'walk' {
        # Run as the new walk user over its own SSH logon.
        if ($Rest.Count -lt 2 -or $Rest.Count -gt 3 -or $Rest[0] -notmatch '^(pypi|wheel)$') {
            Fail 'usage: windows-walk.ps1 walk pypi|wheel OPERATOR [WHEEL]' 2
        }
        $mode = $Rest[0]
        $operator = $Rest[1]
        $wheel = if ($Rest.Count -eq 3) { $Rest[2] } else { '' }
        if (($mode -eq 'wheel') -ne [bool]$wheel) { Fail 'Supply one wheel for wheel mode; none for pypi' 2 }
        $root = Join-Path $HOME 'clean-install'
        $evidence = Join-Path $root 'evidence'
        $repo = Join-Path $root 'repo'
        if ((Test-Path $root) -or (Get-Command coga -ErrorAction SilentlyContinue)) {
            Fail 'This is not a clean install; walk with a new user' 2
        }
        New-Item -ItemType Directory -Force $evidence, $repo | Out-Null
        $transcript = Join-Path $evidence 'transcript.txt'
        $steps = Join-Path $evidence 'steps.txt'

        function Log([string]$Line) {
            Write-Host $Line
            Add-Content -Path $transcript -Value $Line -Encoding UTF8
        }
        function Step([string]$Label, [scriptblock]$Body) {
            Log "`n+ $Label"
            $global:LASTEXITCODE = 0
            $code = 0
            try {
                & $Body 2>&1 | ForEach-Object { Log "$_" }
                $code = $global:LASTEXITCODE
            } catch {
                Log "$_"
                $code = 1
            }
            if ($code -ne 0) {
                $line = "FAIL (exit $code)`t$Label"
                Add-Content -Path $steps -Value $line -Encoding UTF8
                Write-Host $line
                exit $code
            }
            Add-Content -Path $steps -Value "PASS`t$Label" -Encoding UTF8
        }

        Step 'whoami' { whoami }
        # Git for Windows is installed machine-wide at provision.
        Step 'git --version' { git --version }
        Step 'irm https://astral.sh/uv/install.ps1 | iex' { Install-Uv }
        Step 'uv --version' { uv --version }
        # Install first; UV_PYTHON_DOWNLOADS=never would block this download.
        Step 'uv python install 3.11' { uv python install 3.11 }
        $env:UV_PYTHON = '3.11'
        $env:UV_PYTHON_DOWNLOADS = 'never'
        Step 'uv python find 3.11' { uv python find 3.11 }
        Step 'check Python 3.11' {
            $python = (& uv python find 3.11 | Select-Object -Last 1)
            $version = (& $python -c 'import sys; print(sys.version.split()[0])')
            "Python $version at $python"
            if ($version -notlike '3.11.*') { [Console]::Error.WriteLine("Python $version is not 3.11"); $global:LASTEXITCODE = 2 }
        }
        if ($mode -eq 'pypi') {
            Step 'uv tool install --python 3.11 coga' { uv tool install --python 3.11 coga }
        } else {
            Step "Get-FileHash $wheel" { (Get-FileHash -Algorithm SHA256 $wheel).Hash }
            Step "uv tool install --python 3.11 $wheel" { uv tool install --python 3.11 $wheel }
        }
        Step 'coga --version' { coga --version }
        Step 'uv tool list' { uv tool list }
        Set-Location $repo
        Step 'git init -b main' { git init -b main }
        Step 'git config --local user.name' { git config --local user.name 'Coga install harness' }
        Step 'git config --local user.email' { git config --local user.email 'install-harness@example.invalid' }
        Step "coga init --user $operator" { coga init --user $operator }
        Step 'coga validate --json' { coga validate --json }
        $passed = 'coga init passed; attended coga ticket and coga build have not run'
        Set-Content -Path (Join-Path $evidence 'init-passed.txt') -Value $passed -Encoding UTF8
        Write-Host $passed
        exit 0
    }
    default {
        Fail 'usage: windows-walk.ps1 baseline | setup | adduser USER | checkout REF REPO_URL | walk pypi|wheel OPERATOR [WHEEL]' 2
    }
}
