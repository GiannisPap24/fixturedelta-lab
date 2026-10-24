# Keep raw arguments: advanced PowerShell parameters would consume Python's -I flag.
$UvArguments = $args

# Project-local tool selection only. Never install tools or change PATH/security policy.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
try {
    $projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    $uv = Join-Path $projectRoot '.tools/uv.exe'
    if (-not (Test-Path -LiteralPath $uv -PathType Leaf)) {
        $uv = (Get-Command uv -CommandType Application -ErrorAction Stop |
            Select-Object -First 1).Source
    }
    $ErrorActionPreference = 'Continue'
    $versionOutput = & $uv --version 2>&1
    $versionExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($versionExit -ne 0 -or [string]$versionOutput -notmatch '^uv (\d+\.\d+\.\d+)(?:\s|$)') {
        throw 'TOOLCHAIN_VERSION'
    }
    $version = [Version]$Matches[1]
    if ($version -lt [Version]'0.13.4' -or $version -ge [Version]'0.14.0') {
        throw 'TOOLCHAIN_VERSION'
    }
}
catch {
    [Console]::Error.WriteLine('TOOLCHAIN_ERROR: uv >=0.13.4,<0.14 is required. Use a trusted patched executable at .tools/uv.exe or first on PATH. No command was run.')
    exit 3
}
$ErrorActionPreference = 'Continue'
& $uv @UvArguments
exit $LASTEXITCODE
