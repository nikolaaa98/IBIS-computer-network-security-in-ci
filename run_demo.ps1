# run_demo.ps1
# IBIS Demo - Industrial Control System Security - Windows Version

Write-Host "=== IBIS Demo - Industrial Control System Security ===" -ForegroundColor Green

$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT_DIR

# Install required packages
Write-Host "Installing required packages..." -ForegroundColor Yellow
pip install -r requirements.txt *>$null

# Create directories
New-Item -ItemType Directory -Force -Path "logs", "pids", "wireshark_captures" | Out-Null

Write-Host "Stopping existing processes..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { 
    $_.ProcessName -eq "python" -or $_.ProcessName -eq "python3" 
} | ForEach-Object {
    $process = $_
    try {
        $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
        if ($cmdline -match "modbus_server|mitm_proxy|modbus_client|ui_server|defense_module") {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    } catch {
        # Ignore errors when stopping processes
    }
}
Start-Sleep -Seconds 3

Write-Host "Cleaning logs..." -ForegroundColor Yellow
Get-ChildItem "logs\*.log" -ErrorAction SilentlyContinue | ForEach-Object {
    Clear-Content $_.FullName -ErrorAction SilentlyContinue
}

Write-Host "Starting Modbus Server on port 5020..." -ForegroundColor Green
$serverJob = Start-Job -ScriptBlock {
    Set-Location $using:ROOT_DIR
    python src\modbus_server.py --port 5020
}
$serverJob.Id | Out-File -FilePath "pids\modbus_server.pid" -Encoding ASCII
Write-Host "Server Job ID: $($serverJob.Id) (port 5020)"
Start-Sleep -Seconds 5

Write-Host "Starting MITM Proxy on port 1502..." -ForegroundColor Green
$proxyJob = Start-Job -ScriptBlock {
    Set-Location $using:ROOT_DIR
    python src\mitm_proxy.py --server-port 5020
}
$proxyJob.Id | Out-File -FilePath "pids\modbus_proxy.pid" -Encoding ASCII
Write-Host "Proxy Job ID: $($proxyJob.Id) (1502 -> 5020)"
Start-Sleep -Seconds 3

Write-Host "Starting Modbus Client..." -ForegroundColor Green
$clientJob = Start-Job -ScriptBlock {
    Set-Location $using:ROOT_DIR
    python src\modbus_client.py --host 127.0.0.1 --port 1502
}
$clientJob.Id | Out-File -FilePath "pids\modbus_client.pid" -Encoding ASCII
Write-Host "Client Job ID: $($clientJob.Id) (port 1502 - PROXY)"
Start-Sleep -Seconds 2

Write-Host "Starting Web UI..." -ForegroundColor Green
$uiProcess = Start-Process -FilePath "python" -ArgumentList "src\ui_server.py" -PassThru -WindowStyle Hidden
$uiProcess.Id | Out-File -FilePath "pids\ui_server.pid" -Encoding ASCII
Write-Host "UI Process ID: $($uiProcess.Id)"
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=== Architecture ===" -ForegroundColor Cyan
Write-Host "Real Server (5020)"
Write-Host "HMI Client -> Proxy (1502) -> Server (5020)"
Write-Host ""
Write-Host "=== Demo is running! ===" -ForegroundColor Green
Write-Host "Web Interface: http://localhost:8080" -ForegroundColor Yellow
Write-Host "Packet Capture: ACTIVE" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop the demo" -ForegroundColor Magenta
Write-Host "==============================" -ForegroundColor Cyan

# Function to stop all services
function Stop-DemoServices {
    Write-Host "`nStopping all services..." -ForegroundColor Yellow
    
    # Stop background jobs
    Get-Job | Where-Object { $_.Name -like "*modbus*" -or $_.Name -like "*proxy*" } | Stop-Job -PassThru | Remove-Job -Force
    
    # Stop UI process
    if (Test-Path "pids\ui_server.pid") {
        $uiPid = Get-Content "pids\ui_server.pid" -ErrorAction SilentlyContinue
        if ($uiPid) {
            Get-Process -Id $uiPid -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        }
    }
    
    # Kill any remaining Python processes related to our demo
    Get-Process -Name "python", "python3" -ErrorAction SilentlyContinue | Where-Object { 
        $_.ProcessName -eq "python" -or $_.ProcessName -eq "python3" 
    } | ForEach-Object {
        $process = $_
        try {
            $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
            if ($cmdline -match "modbus_server|mitm_proxy|modbus_client|ui_server|defense_module") {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {
            # Ignore errors
        }
    }
    
    Write-Host "Demo stopped successfully" -ForegroundColor Green
}

# Handle Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Stop-DemoServices
}

# Monitor services and keep script alive
try {
    do {
        Start-Sleep -Seconds 10
        
        # Check if UI server is still running
        if (Test-Path "pids\ui_server.pid") {
            $uiPid = Get-Content "pids\ui_server.pid" -ErrorAction SilentlyContinue
            if ($uiPid -and -not (Get-Process -Id $uiPid -ErrorAction SilentlyContinue)) {
                Write-Host "UI server stopped - ending demo" -ForegroundColor Red
                break
            }
        } else {
            Write-Host "UI server PID file missing - ending demo" -ForegroundColor Red
            break
        }
        
        # Optional: Check if other services are still running
        $jobsRunning = @(Get-Job | Where-Object { $_.State -eq "Running" }).Count
        if ($jobsRunning -eq 0) {
            Write-Host "All background jobs stopped - ending demo" -ForegroundColor Red
            break
        }
        
    } while ($true)
}
finally {
    Stop-DemoServices
    Unregister-Event -SourceIdentifier PowerShell.Exiting -ErrorAction SilentlyContinue
}