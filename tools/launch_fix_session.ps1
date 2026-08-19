# Opens a fresh Claude Code session to carry out the round-2 fixes.
#
# Deliberately a NEW session rather than --continue: the previous one has been
# idle for hours with 165 uncommitted files, and resuming a stale conversation
# risks it re-running work it believes is unfinished. A fresh session reads the
# fix list and the working tree as they actually are.
#
# It runs interactively and will ask before acting, in this window, where you
# can see and answer it.

$ErrorActionPreference = 'Stop'
$project = 'C:\Projects\The Echoing Void'
Set-Location -LiteralPath $project

$admin = [Security.Principal.WindowsPrincipal]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host ''
Write-Host '  The Echoing Void - round 2 fixes' -ForegroundColor Cyan
Write-Host ('  {0}' -f $project) -ForegroundColor DarkGray
Write-Host ('  elevated: {0}' -f $admin) -ForegroundColor DarkGray
Write-Host '  brief: docs\FIXES_round2.md' -ForegroundColor DarkGray
Write-Host ''

$prompt = @'
Read docs/FIXES_round2.md in full before touching anything, then carry out all seven fixes in it. Every item came from the player watching the mod run in game, so treat each as confirmed rather than hypothetical.

Context you need first: another session has left 165 uncommitted files in this working tree - a Hushwater fluid, a full void crop set, and worldgen for both. That work is good and must be preserved. Do not revert it, do not stash it, and do not run destructive git commands. You are fixing defects in it, not replacing it. It also left docs/HARNESS_findings.md, which is worth reading.

Two items are known-wrong code where the cause is already established, so do not re-investigate them from scratch:

Item 3 - GroundSupportProcessor.java takes an edges_only flag and tools/gen_structures.py passes it as True. That legs only the perimeter columns, which is exactly why every structure piece now sits on a rim above hollow space. Remove the flag entirely rather than flipping it to false, extend EVERY bottom-layer column, and fill with a constant echoing_void:raw_phonolite rather than copying whatever block happens to be lowest in each column. Doing that also fixes item 5 for free, because the stacked-slab legs under bridge_stair only exist while the support copies the lowest block.

Item 7 - the earlier lantern audit was too narrow. It walked up through chains and accepted any solid anchor, so it missed lanterns anchored on slabs, stairs and fences, and it never considered the archway lamps at all. Redo it across every generated .nbt and connect the archway lanterns with chain as the player asks.

Item 2 has a diagnosis you should verify rather than trust: all six hushwater PNGs exist and IClientFluidTypeExtensions is implemented correctly, so the black-and-purple is almost certainly that the sprites are never stitched into the block atlas - there is no assets/echoing_void/atlases/ directory at all. Confirm that is the cause before fixing it.

Item 6 carries a direct ruling from the player which you must not re-litigate: the chimney cap at tools/gen_structures.py:664 becomes "bottom". The workbench surface, the table tops and the bridge kerbs stay "top". Every other top-half slab defaults to "bottom", and record a one-line reason for any that survive as "top".

Item 1 is a design task and belongs to Antigravity, not to you. The fix list explains how to invoke that CLI, including that -p must come last or the prompt is silently swallowed, and that briefs about shape need PNGs and pixel maps rather than adjectives.

Verification is not optional and inspection does not count. After each change run the three gates - verify_textures.py, verify_models.py, check_creative_tabs.py - and then boot a server and confirm run/logs/latest.log contains zero occurrences of Unbound values, Failed to parse, Errors in element and ERROR]. Generating valid JSON and compiling green does NOT prove a datapack loads; that mistake previously took the whole worldgen registry down at boot. Note also that a headless server with no player stops ticking the world after 60 seconds, so any test that waits on the world needs pause-when-empty-seconds=0.

Do not commit or push unless the player asks. When you are done, summarise what you changed, what you verified and how, and what you could not confirm.
'@

$claude = 'C:\Users\admin\.local\bin\claude.exe'
if (-not (Test-Path -LiteralPath $claude)) {
    $found = (Get-Command claude -ErrorAction SilentlyContinue).Source
    if ($found) { $claude = $found } else {
        Write-Host '  ERROR: claude.exe not found.' -ForegroundColor Red
        Read-Host '  press Enter to close'; exit 1
    }
}

$log = Join-Path $project 'build\fix_session_launch.txt'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
"[{0}] starting {1}" -f (Get-Date -Format o), $claude | Add-Content -Path $log
"[{0}] prompt {1} chars" -f (Get-Date -Format o), $prompt.Length | Add-Content -Path $log

Write-Host '  starting...' -ForegroundColor Cyan
Write-Host ''

try {
    & $claude $prompt
    "[{0}] exited {1}" -f (Get-Date -Format o), $LASTEXITCODE | Add-Content -Path $log
} catch {
    "[{0}] THREW {1}" -f (Get-Date -Format o), $_.Exception.Message | Add-Content -Path $log
    Write-Host ('  ERROR: ' + $_.Exception.Message) -ForegroundColor Red
}

Write-Host ''
Write-Host '  (session ended - window kept open)' -ForegroundColor DarkGray
