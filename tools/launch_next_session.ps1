# Opens an interactive Claude Code session in this project, already primed with
# the handoff brief. Meant to be started elevated via Start-Process -Verb RunAs.
#
# A script file rather than an inline -Command string on purpose: the prompt has
# to survive Start-Process -> powershell -> claude, and nested quoting through
# three layers is how launchers silently end up passing half a prompt.

$ErrorActionPreference = 'Stop'

$project = 'C:\Projects\The Echoing Void'
Set-Location -LiteralPath $project

Write-Host ''
Write-Host '  The Echoing Void - next session' -ForegroundColor Cyan
Write-Host ('  {0}' -f $project) -ForegroundColor DarkGray
Write-Host ('  elevated: {0}' -f ([Security.Principal.WindowsPrincipal]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))) -ForegroundColor DarkGray
Write-Host '  brief: docs\HANDOFF_next_session.md' -ForegroundColor DarkGray
Write-Host ''

$prompt = @'
Read docs/HANDOFF_next_session.md in full before doing anything, then implement the five features it scopes out: (1) the Dead Water void fluid, with lakes, streams and waterfalls that spill off the floating islands, (2) void crops plus moss tillable into a void-only farmland and a Resonant Bread food, (3) a farm structure showing the encampment traders actually farming, (4) cave generation for the Hollow Horizon with the ores easier to find in it, and (5) reworked structure INTERIORS only - the exteriors are signed off and must not change.

Start with the fluid, because it also gives the player a way up and down from the floating islands.

Two rules from that brief matter more than the rest, so I am repeating them here. First: generating valid JSON and compiling green does NOT prove a datapack loads - a previous worldgen change did both and still took the entire registry down at boot, so after any worldgen, structure or registry change you must boot a server with python tools/test_structures.py and confirm the log has zero Unbound values, Failed to parse, or Errors in element. Second: every asset in this repo is generated from Python under tools/, so never hand-edit a PNG or a generated JSON - edit the generator and re-run it.

Also note docs/bug_sweep_findings.json holds 38 already-investigated findings with file and line evidence, several of them directly about cave carvers and worldgen placers. Read it before investigating anything yourself.
'@

# Absolute path on purpose. The first attempt at this launcher called `claude`
# by name, and the elevated -NoProfile shell could not resolve it - so the
# window opened and nothing started, silently, because nothing was there to
# print an error.
$claude = 'C:\Users\admin\.local\bin\claude.exe'
if (-not (Test-Path -LiteralPath $claude)) {
    $found = (Get-Command claude -ErrorAction SilentlyContinue).Source
    if ($found) { $claude = $found }
    else {
        Write-Host '  ERROR: claude.exe not found. Fix the path in this script.' -ForegroundColor Red
        Read-Host '  press Enter to close'
        exit 1
    }
}
Write-Host ('  launching: {0}' -f $claude) -ForegroundColor DarkGray
Write-Host ''

# Markers to a log file, because the first two attempts closed without
# leaving any trace of why - and a launcher that fails invisibly is worse
# than one that fails loudly.
$log = 'C:\Projects\The Echoing Void\build\launch_log.txt'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
"[{0}] about to start {1}" -f (Get-Date -Format o), $claude | Add-Content -Path $log
"[{0}] prompt is {1} chars" -f (Get-Date -Format o), $prompt.Length | Add-Content -Path $log

try {
    & $claude $prompt
    "[{0}] claude exited with {1}" -f (Get-Date -Format o), $LASTEXITCODE | Add-Content -Path $log
} catch {
    "[{0}] THREW: {1}" -f (Get-Date -Format o), $_.Exception.Message | Add-Content -Path $log
    Write-Host ('  ERROR: ' + $_.Exception.Message) -ForegroundColor Red
}

Write-Host ''
Write-Host '  (session ended - window kept open)' -ForegroundColor DarkGray
