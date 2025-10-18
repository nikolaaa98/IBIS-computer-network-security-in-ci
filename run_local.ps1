param(
    [int]$ServerPort = 502,
    [int]$ProxyPort = 1502
)
 
$ErrorActionPreference = "Stop"
 
# Paths
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvDir = Join-Path $RootDir ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"
$Pip = Join-Path $VenvDir "Scripts\pip.exe"
$ServerHost = "127.0.0.1"
$ProxyHost = "127.0.0.1"
$ClientInterval = 3
 
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Modbus Testing Environment" -ForegroundColor Cyan
Write-Host "  Launching 3 Console Windows" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project root: $RootDir"
Write-Host "Server: $ServerHost`:$ServerPort"
Write-Host "Proxy (HMI endpoint): $ProxyHost`:$ProxyPort"
Write-Host ""
 
# 1) Create venv if needed
if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VenvDir
    Start-Sleep -Seconds 2
 
    if (-not (Test-Path $Python)) {
        Write-Host "ERROR: Virtual environment creation failed!" -ForegroundColor Red
        Write-Host "Ensure Python is installed and on PATH." -ForegroundColor Red
        exit 1
    }
    Write-Host "Virtual environment created." -ForegroundColor Green
}
 
# 2) Install requirements
Write-Host "Installing requirements..." -ForegroundColor Yellow
$RequirementsFile = Join-Path $RootDir "requirements.txt"
if (Test-Path $RequirementsFile) {
    & $Pip install --upgrade pip --quiet
    & $Pip install -r $RequirementsFile --quiet
    Write-Host "Requirements installed." -ForegroundColor Green
} else {
    Write-Host "WARNING: requirements.txt not found" -ForegroundColor Yellow
}
 
Write-Host ""
Write-Host "Opening console windows..." -ForegroundColor Yellow
Write-Host ""
 
# 3) Start MODBUS SERVER in its own console
Write-Host "  [1/3] Opening MODBUS SERVER console..." -ForegroundColor Green
$serverScript = Join-Path $RootDir "src\modbus_server.py"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& {" +
    "  `$Host.UI.RawUI.WindowTitle = 'MODBUS SERVER - Port $ServerPort';" +
    "  Write-Host '========================================'  -ForegroundColor Green;" +
    "  Write-Host '  MODBUS SERVER'  -ForegroundColor Green;" +
    "  Write-Host '  Listening on: $ServerHost`:$ServerPort'  -ForegroundColor Green;" +
    "  Write-Host '========================================'  -ForegroundColor Green;" +
    "  Write-Host '';" +
    "  & '$Python' '$serverScript' --host $ServerHost --port $ServerPort" +
    "}"
)
 
Start-Sleep -Seconds 2
 
# 4) Start MITM PROXY in its own console
Write-Host "  [2/3] Opening MITM PROXY console..." -ForegroundColor Magenta
$proxyScript = Join-Path $RootDir "src\mitm_proxy.py"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& {" +
    "  `$Host.UI.RawUI.WindowTitle = 'MITM PROXY - Port $ProxyPort';" +
    "  Write-Host '========================================'  -ForegroundColor Magenta;" +
    "  Write-Host '  MITM PROXY (Traffic Interceptor)'  -ForegroundColor Magenta;" +
    "  Write-Host '  Listening on: 0.0.0.0`:$ProxyPort'  -ForegroundColor Magenta;" +
    "  Write-Host '  Forwarding to: $ServerHost`:$ServerPort'  -ForegroundColor Magenta;" +
    "  Write-Host '========================================'  -ForegroundColor Magenta;" +
    "  Write-Host '';" +
    "  & '$Python' '$proxyScript' --proxy-host 0.0.0.0 --proxy-port $ProxyPort --server-host $ServerHost --server-port $ServerPort" +
    "}"
)
 
Start-Sleep -Seconds 2
 
# 5) Start MODBUS CLIENT in its own console
Write-Host "  [3/3] Opening MODBUS CLIENT console..." -ForegroundColor Yellow
$clientScript = Join-Path $RootDir "src\modbus_client.py"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& {" +
    "  `$Host.UI.RawUI.WindowTitle = 'MODBUS CLIENT - Polling every ${ClientInterval}s';" +
    "  Write-Host '========================================'  -ForegroundColor Yellow;" +
    "  Write-Host '  MODBUS CLIENT'  -ForegroundColor Yellow;" +
    "  Write-Host '  Connecting to: $ProxyHost`:$ProxyPort'  -ForegroundColor Yellow;" +
    "  Write-Host '  Poll interval: ${ClientInterval}s'  -ForegroundColor Yellow;" +
    "  Write-Host '========================================'  -ForegroundColor Yellow;" +
    "  Write-Host '';" +
    "  & '$Python' '$clientScript' --host $ProxyHost --port $ProxyPort --interval $ClientInterval" +
    "}"
)
 
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  ALL CONSOLES OPENED!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "You should now see 3 console windows:" -ForegroundColor Cyan
Write-Host "  1. MODBUS SERVER (Green) - Port $ServerPort" -ForegroundColor Green
Write-Host "  2. MITM PROXY (Magenta) - Port $ProxyPort" -ForegroundColor Magenta
Write-Host "  3. MODBUS CLIENT (Yellow) - Polls every ${ClientInterval}s" -ForegroundColor Yellow
Write-Host ""
Write-Host "To stop: Close each console window (Ctrl+C or click X)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to close this launcher window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")