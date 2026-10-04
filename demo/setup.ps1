param([string]$CandidateDirectory, [string]$LinuxSettingsBinary)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$distro = 'Convertibled-Demo'
function Wsl([string[]]$Arguments) {
    & wsl.exe -d $distro -u root --exec @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Runtime setup failed: $($Arguments[0])" }
}
$installed = (& wsl.exe --list --quiet) -replace "`0", ''
if ($installed.Trim() -notcontains $distro) {
    & wsl.exe --install FedoraLinux-44 --name $distro --location (Join-Path $env:LOCALAPPDATA 'convertibled-demo') --no-launch
    if ($LASTEXITCODE -ne 0) { throw 'Fedora WSL installation failed.' }
    Wsl @('touch','/etc/convertibled-demo-runtime')
}
Wsl @('test','-f','/etc/convertibled-demo-runtime')
$linuxRepo = (Wsl @('wslpath','-a',$repo)).Trim()
Wsl @('bash',"$linuxRepo/demo/native/setup.sh")
Push-Location $repo
try {
    & npm.cmd --prefix extension ci
    if ($LASTEXITCODE -ne 0) { throw 'Extension dependencies failed.' }
    if ($CandidateDirectory -and $LinuxSettingsBinary) { throw 'Choose one settings binary source.' }
    if ($CandidateDirectory) {
        $candidate = (Resolve-Path $CandidateDirectory).Path
        $record = Get-Content (Join-Path $candidate 'candidate.json') -Raw | ConvertFrom-Json
        if ($record.commit -notmatch '^[a-f0-9]{40}$' -or $record.artifact -ne 'convertibled-fedora44-x86_64.tar.gz') { throw 'Invalid candidate record.' }
        $bundle = Join-Path $candidate $record.artifact
        if ((Get-FileHash $bundle -Algorithm SHA256).Hash.ToLowerInvariant() -ne $record.artifact_sha256) { throw 'Candidate hash mismatch.' }
        & git diff --quiet $record.commit -- crates Cargo.toml Cargo.lock
        if ($LASTEXITCODE -ne 0) { throw 'Settings sources differ or candidate commit is unavailable. Build the current Linux binary instead.' }
        $extract = Join-Path $repo '.tools/native-bin'
        New-Item -ItemType Directory -Force $extract | Out-Null
        & tar -xzf $bundle -C $extract bin/convertibled-settings
        if ($LASTEXITCODE -ne 0) { throw 'Candidate extraction failed.' }
        $LinuxSettingsBinary = Join-Path $extract 'bin/convertibled-settings'
    }
    if ($LinuxSettingsBinary) {
        $binary = (Resolve-Path $LinuxSettingsBinary).Path
        $linuxBinary = (Wsl @('wslpath','-a',$binary)).Trim()
        $destination = '/home/demo/.local/state/convertibled-native-demo/bin'
        Wsl @('install','-d','-o','demo','-g','demo',$destination)
        Wsl @('install','-m','755','-o','demo','-g','demo',$linuxBinary,"$destination/convertibled-settings")
        if ($CandidateDirectory) {
            [IO.File]::WriteAllText((Join-Path $repo '.tools/native-settings-commit'), $record.commit)
        } elseif (Test-Path (Join-Path $repo '.tools/native-settings-commit')) {
            Remove-Item -LiteralPath (Join-Path $repo '.tools/native-settings-commit')
        }
    } else { Write-Output 'Shell preview ready. Settings requires -LinuxSettingsBinary or -CandidateDirectory.' }
} finally { Pop-Location }
Write-Output 'Setup complete. Start with demo/start.cmd.'
