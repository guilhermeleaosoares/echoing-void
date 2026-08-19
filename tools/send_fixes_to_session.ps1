# Delivers the round-2 fix list to the working session, resuming its existing
# conversation rather than starting a fresh one.
#
# `claude --continue` picks up the most recent conversation in this directory,
# so the session keeps everything it has learned about the fluid, the crops and
# the harness quirks - a new session would start cold and re-tread all of it.
#
# Run elevated:
#   Start-Process -Verb RunAs powershell -ArgumentList '-NoExit','-NoProfile',
#     '-ExecutionPolicy','Bypass','-File','<this file>'

$ErrorActionPreference = 'Stop'
$project = 'C:\Projects\The Echoing Void'
Set-Location -LiteralPath $project

# Two Claude sessions sharing one conversation will fight over it. Refuse rather
# than corrupt: the existing window is the one that should receive this.
$busy = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match 'runServer|gradlew'
}).Count
if ($busy -gt 0) {
    Write-Host ''
    Write-Host "  A build or server is running ($busy processes)." -ForegroundColor Yellow
    Write-Host '  The working session is probably still mid-task.' -ForegroundColor Yellow
    Write-Host '  Paste the brief into THAT window instead, or wait for it to go quiet.' -ForegroundColor Yellow
    Write-Host ''
    $go = Read-Host '  Continue anyway and resume the conversation here? (y/N)'
    if ($go -ne 'y') { Write-Host '  aborted.'; Read-Host '  press Enter to close'; exit 0 }
}

$prompt = @'
Read docs/FIXES_round2.md in full, then carry out all seven fixes. They come from the player after seeing the mod running in game, so treat every one as confirmed rather than hypothetical.

Two of them are known-wrong code with the cause already found, so do not re-investigate from scratch. Item 3: GroundSupportProcessor takes an edges_only flag that gen_structures.py passes as True, which legs only the perimeter columns and is exactly why every piece sits on a rim over hollow space - delete the flag rather than flipping it, extend EVERY bottom-layer column, and fill with constant echoing_void:raw_phonolite instead of copying whatever block happened to be lowest. That also fixes item 5 for free, because the bridge_stair slab legs only exist while the support copies the lowest block. Item 7: the earlier lantern audit was too narrow - it accepted any solid anchor and never considered the archway lamps at all, so redo it properly across every generated nbt and chain the archway lanterns as the player asks.

Item 2 has a diagnosis to verify rather than trust: the hushwater PNGs all exist and IClientFluidTypeExtensions is correct, so the black-and-purple is almost certainly that the sprites are never stitched into the block atlas - there is no assets/echoing_void/atlases/ directory at all. Confirm that before fixing it.

Item 6 carries a direct ruling from the player that you must not re-litigate: the chimney cap at gen_structures.py:664 becomes "bottom", while the workbench surface, the table tops and the bridge kerbs stay "top". The remaining top-half slabs default to "bottom" and want a one-line reason recorded if any survive.

Item 1 is a design task for Antigravity, not for you. docs/FIXES_round2.md explains how to invoke it, including that -p must come last or the prompt is silently swallowed, and that shape briefs need PNGs and pixel maps rather than adjectives.

Verify everything in a running game, not by inspection: run the three gates, then boot a server and confirm zero Unbound values, Failed to parse, Errors in element and ERROR] in run/logs/latest.log. Your own HARNESS_findings note about the server pausing when empty applies to any test that waits on the world to act.
'@

$claude = 'C:\Users\admin\.local\bin\claude.exe'
if (-not (Test-Path -LiteralPath $claude)) {
    $found = (Get-Command claude -ErrorAction SilentlyContinue).Source
    if ($found) { $claude = $found } else {
        Write-Host '  ERROR: claude.exe not found.' -ForegroundColor Red
        Read-Host '  press Enter to close'; exit 1
    }
}

Write-Host ''
Write-Host '  resuming the working session with the round-2 fix list...' -ForegroundColor Cyan
Write-Host ''

& $claude --continue $prompt

Write-Host ''
Write-Host '  (session ended - window kept open)' -ForegroundColor DarkGray
