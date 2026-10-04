param([switch]$Check)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$distro = 'Convertibled-Demo'
function Invoke-Wsl([string[]]$Arguments) {
    $result = & wsl.exe -d $distro -u demo --exec @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Demo command failed: $($Arguments[0])" }
    return $result
}
function Get-DemoState {
    $ErrorActionPreference = 'Continue'
    $latest = & wsl.exe -d $distro -u demo --exec cat /home/demo/.local/state/convertibled-native-demo/latest 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    $address = & wsl.exe -d $distro -u demo --exec cat "$($latest.Trim())/bus-address" 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    $state = & wsl.exe -d $distro -u demo --exec env "DBUS_SESSION_BUS_ADDRESS=$($address.Trim())" gdbus call --session --timeout 1 --dest org.convertibled.Demo --object-path /org/convertibled/Demo --method org.convertibled.Demo.Inspect 2>$null
    if ($LASTEXITCODE -eq 0) { return $state }
    return $null
}
$installed = (& wsl.exe --list --quiet) -replace "`0", ''
if ($installed.Trim() -notcontains $distro) {
    throw 'Native demo runtime missing. Run demo/setup.ps1 first; see demo/README.md.'
}
$current = Get-DemoState
if ($current) {
    Write-Output 'Native demo is already running: Mutter Development Kit + convertibled Demo-Steuerung.'
    Write-Output $current
    exit 0
}
if ($Check) { throw 'Native demo is not running.' }
Push-Location $repo
try {
    $provenance = Join-Path $repo '.tools/native-settings-commit'
    if (Test-Path $provenance) {
        $sourceCommit = [IO.File]::ReadAllText($provenance).Trim()
        if ($sourceCommit -notmatch '^[a-f0-9]{40}$') { throw 'Invalid settings source record.' }
        & git diff --quiet $sourceCommit -- crates Cargo.toml Cargo.lock
        if ($LASTEXITCODE -ne 0) { throw 'Settings sources changed. Re-run setup with a current Linux build or matching CI candidate.' }
    }
    & npm.cmd --prefix extension run build
    if ($LASTEXITCODE -ne 0) { throw 'Production extension build failed.' }
    $linuxRepo = (Invoke-Wsl @('wslpath','-a',$repo)).Trim()
    $output = Join-Path $repo '.tools/native-demo.out.log'
    $errors = Join-Path $repo '.tools/native-demo.err.log'
    New-Item -ItemType Directory -Force (Join-Path $repo '.tools') | Out-Null
    $process = Start-Process wsl.exe -ArgumentList @('-d',$distro,'-u','demo','--exec','bash',('"{0}/demo/native/run.sh"' -f $linuxRepo)) -WindowStyle Hidden -RedirectStandardOutput $output -RedirectStandardError $errors -PassThru
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        $process.Refresh()
        if ($process.HasExited) { throw "Native demo exited. See $errors" }
        if ((Get-Content $output -Raw -ErrorAction SilentlyContinue) -match 'Native demo ready') {
            $state = Get-DemoState
            if ($state) {
                Write-Output 'Native GNOME demo started. Use the separate scenario controls window.'
                Write-Output $state
                exit 0
            }
        }
    }
    throw "Native demo has not reported ready. See $output and $errors"
} finally { Pop-Location }
