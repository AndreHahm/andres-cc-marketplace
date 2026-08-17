<#
Manually delete old session-scratchpad directories for this project
(%LOCALAPPDATA%\Temp\claude\<sanitized-repo-path>\<session-uuid>\).
rm -rf is blocked when Claude runs it, so this is meant to be run by hand,
from your own terminal, not from inside a Claude Code session.
#>
param(
    [int]$Days = 7
)

$ErrorActionPreference = 'Stop'

if ($Days -lt 0) {
    Write-Error "Days threshold must be a non-negative integer."
    exit 1
}

$repoRoot = $null
try {
    $repoRoot = (git rev-parse --show-toplevel 2>$null)
} catch {}
if (-not $repoRoot) {
    Write-Error "Not inside a git repository."
    exit 1
}
$repoRoot = (Resolve-Path $repoRoot).Path

$sanitized = $repoRoot -replace ':', '-' -replace '\\', '-'
$target = Join-Path $env:LOCALAPPDATA "Temp\claude\$sanitized"

if (-not (Test-Path $target)) {
    Write-Host "No scratchpad directory found at: $target"
    exit 0
}

Write-Host "Scanning $target for session directories older than $Days day(s)..."
Write-Host ""

$cutoff = (Get-Date).AddDays(-$Days)
$toDelete = @()
$totalBytes = 0

Get-ChildItem -Path $target -Directory | ForEach-Object {
    $dir = $_
    $newest = @($dir) + (Get-ChildItem -Path $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue) |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $lastWrite = $newest.LastWriteTime

    if ($lastWrite -lt $cutoff) {
        $sizeBytes = (Get-ChildItem -Path $dir.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum).Sum
        if (-not $sizeBytes) { $sizeBytes = 0 }
        $ageDays = [math]::Floor(((Get-Date) - $lastWrite).TotalDays)
        $sizeMB = [math]::Round($sizeBytes / 1MB, 2)
        Write-Host "  $($dir.Name)  (${ageDays}d old, ${sizeMB} MB)"
        $toDelete += $dir
        $totalBytes += $sizeBytes
    }
}

if ($toDelete.Count -eq 0) {
    Write-Host "Nothing older than $Days day(s) to delete."
    exit 0
}

Write-Host ""
$plural = if ($toDelete.Count -eq 1) { "y" } else { "ies" }
$totalMB = [math]::Round($totalBytes / 1MB, 2)
Write-Host "$($toDelete.Count) director$plural found, totaling $totalMB MB."
$answer = Read-Host "Delete these directories? [y/N]"

if ($answer -match '^(y|yes)$') {
    foreach ($dir in $toDelete) {
        Remove-Item -Path $dir.FullName -Recurse -Force
        Write-Host "Deleted: $($dir.FullName)"
    }
    Write-Host "Done."
} else {
    Write-Host "Cancelled - nothing deleted."
}
