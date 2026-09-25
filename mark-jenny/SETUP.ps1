# Mark-Imti - Install dependencies (run once after cloning)
$Root = $PSScriptRoot
Write-Host "=== Mark-Imti SETUP ==="
Write-Host ""

# 1. Backend venv
if (-not (Test-Path "$Root\backend\venv\Scripts\python.exe")) {
    Write-Host "[1/3] Creating Python virtual environment..."
    python -m venv "$Root\backend\venv"
} else {
    Write-Host "[1/3] Python venv already exists"
}

# 2. Backend deps
Write-Host "[2/3] Installing backend dependencies..."
& "$Root\backend\venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& "$Root\backend\venv\Scripts\python.exe" -m pip install -r "$Root\backend\requirements.txt" --quiet

# 3. Frontend deps
Write-Host "[3/3] Installing frontend dependencies (this may take a few minutes)..."
if (-not (Test-Path "$Root\frontend\node_modules")) {
    Push-Location "$Root\frontend"
    npm install
    Pop-Location
} else {
    Write-Host "      frontend modules already exist"
}

Write-Host ""
Write-Host "Setup complete! Now run START-APP.bat (double-click)."
Write-Host "Open http://localhost:3000"
Read-Host "Press Enter to exit"