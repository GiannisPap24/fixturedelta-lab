param([string]$OutputDirectory = 'artifacts/demo')

# Run from the project root. Never change execution policy or create an environment.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
try {
    $projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    if ((Get-Location).Provider.Name -ne 'FileSystem' -or
        (Get-Location).Path -ne $projectRoot) { throw 'DEMO_PROJECT' }
    $manifest = Get-Content -LiteralPath (Join-Path $projectRoot 'pyproject.toml') -Raw
    if ($manifest -notmatch '(?m)^name\s*=\s*"fixturedelta-lab"\s*$' -or
        -not (Test-Path -LiteralPath (Join-Path $projectRoot 'src/fixturedelta_lab/cli.py') -PathType Leaf)) {
        throw 'DEMO_PROJECT'
    }
    $python = Join-Path $projectRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
        -not (Test-Path -LiteralPath (Join-Path $projectRoot 'uv.lock') -PathType Leaf)) {
        throw 'DEMO_ENVIRONMENT'
    }
    # Refuse an inherited uv override that could create/use an unrelated environment.
    if ($env:UV_PROJECT_ENVIRONMENT -and
        [IO.Path]::GetFullPath($env:UV_PROJECT_ENVIRONMENT) -ne
        [IO.Path]::GetFullPath((Join-Path $projectRoot '.venv'))) { throw 'DEMO_ENVIRONMENT' }
    $uv = Join-Path $PSScriptRoot 'uv.ps1'
    # Capture native stderr too: expected CLI failures are handled by the Python verifier.
    # Do not echo uv diagnostics, which may include machine paths.
    $ErrorActionPreference = 'Continue'
    $lockOutput = & $uv lock --check --offline 2>&1
    $lockExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($lockExit -ne 0) { throw 'DEMO_LOCK' }
    $ErrorActionPreference = 'Continue'
    $demoOutput = & $uv run --locked --offline --no-python-downloads $python -I `
        scripts/demo.py --report-dir $OutputDirectory 2>&1
    $demoExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($demoExit -ne 0) {
        foreach ($line in $demoOutput) {
            if ([string]$line -match '^DEMO FAIL:') { [Console]::Error.WriteLine([string]$line) }
        }
        throw 'DEMO_INVARIANT'
    }
    foreach ($line in $demoOutput) {
        if ([string]$line -match '^DEMO ') { Write-Output ([string]$line) }
    }
    exit 0
}
catch {
    [Console]::Error.WriteLine('DEMO FAIL: Run from the project root with the existing cached .venv and a fresh directory under artifacts; verify lock, file access and demo invariants.')
    exit 1
}
