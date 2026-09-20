# MARK IMTI - Hidden background launcher (no visible terminal windows)
# Used by START-APP.bat. Launches backend + frontend with hidden windows
# and writes their PIDs so they can be stopped with STOP-APP.bat.

$Root = $PSScriptRoot
$BackendLog = "$Root\logs\backend.log"
$FrontendLog = "$Root\logs\frontend.log"
$PidFile = "$Root\logs\app.pids"
$BackendPy = "$Root\backend\venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path "$Root\logs" | Out-Null

# --- Backend (port 8000) ---
if (Test-Path $BackendPy) {
    $Backend = Start-Process -FilePath $BackendPy `
        -ArgumentList "main.py" `
        -WorkingDirectory "$Root\backend" `
        -WindowStyle Hidden `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError "$BackendLog.err" `
        -PassThru
} else {
    $Backend = Start-Process -FilePath "python" `
        -ArgumentList "main.py" `
        -WorkingDirectory "$Root\backend" `
        -WindowStyle Hidden `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError "$BackendLog.err" `
        -PassThru
}

# --- Frontend (port 3000) ---
$Frontend = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run","dev","--","--webpack" `
    -WorkingDirectory "$Root\frontend" `
    -WindowStyle Hidden `
    -RedirectStandardOutput $FrontendLog `
    -RedirectStandardError "$FrontendLog.err" `
    -PassThru

# Save PIDs for STOP-APP.bat
"$($Backend.Id) $($Frontend.Id)" | Set-Content -Path $PidFile

Write-Host "MARK IMTI started hidden."
Write-Host "Backend : http://localhost:8000  (PID $($Backend.Id))"
Write-Host "Frontend: http://localhost:3000  (PID $($Frontend.Id))"
Write-Host "Logs    : $Root\logs"
