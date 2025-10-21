# run_demo.ps1
# IBIS Demo - Industrial Control System Security - Windows Version
# IDENTIČNO MAC SKRIPTI

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
Start-Process -FilePath "python" -ArgumentList "src\modbus_server.py --port 5020" -RedirectStandardOutput "logs\modbus_server.log" -RedirectStandardError "logs\modbus_server.log" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2
$serverProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { 
    $_.ProcessName -eq "python" -and (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -match "modbus_server"
}
if ($serverProcess) {
    $serverProcess.Id | Out-File -FilePath "pids\modbus_server.pid" -Encoding ASCII
    Write-Host "Server PID: $($serverProcess.Id) (port 5020)"
}
Start-Sleep -Seconds 3

Write-Host "Starting MITM Proxy on port 1502..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "src\mitm_proxy.py --server-port 5020" -RedirectStandardOutput "logs\modbus_proxy.log" -RedirectStandardError "logs\modbus_proxy.log" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2
$proxyProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { 
    $_.ProcessName -eq "python" -and (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -match "mitm_proxy"
}
if ($proxyProcess) {
    $proxyProcess.Id | Out-File -FilePath "pids\modbus_proxy.pid" -Encoding ASCII
    Write-Host "Proxy PID: $($proxyProcess.Id) (1502 -> 5020)"
}
Start-Sleep -Seconds 2

Write-Host "Starting Modbus Client..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "src\modbus_client.py --host 127.0.0.1 --port 1502" -RedirectStandardOutput "logs\modbus_client.log" -RedirectStandardError "logs\modbus_client.log" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2
$clientProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { 
    $_.ProcessName -eq "python" -and (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -match "modbus_client"
}
if ($clientProcess) {
    $clientProcess.Id | Out-File -FilePath "pids\modbus_client.pid" -Encoding ASCII
    Write-Host "Client PID: $($clientProcess.Id) (port 1502 - PROXY)"
}
Start-Sleep -Seconds 2

Write-Host "Starting Web UI..." -ForegroundColor Green
$uiProcess = Start-Process -FilePath "python" -ArgumentList "src\ui_server.py" -RedirectStandardOutput "logs\ui_server.log" -RedirectStandardError "logs\ui_server.log" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2
if ($uiProcess) {
    $uiProcess.Id | Out-File -FilePath "pids\ui_server.pid" -Encoding ASCII
    Write-Host "UI PID: $($uiProcess.Id)"
}
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "=== Architecture ===" -ForegroundColor Cyan
Write-Host "Real Server (5020)"
Write-Host "HMI Client -> Proxy (1502) -> Server (5020)"
Write-Host ""
Write-Host "=== Demo is running! ===" -ForegroundColor Green
Write-Host "Web Interface: http://localhost:8080" -ForegroundColor Yellow
Write-Host "Defense System: READY (start from UI)" -ForegroundColor Yellow
Write-Host "Command Injection: Targets Defense System (port 502)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop the demo" -ForegroundColor Magenta
Write-Host "==============================" -ForegroundColor Cyan

# Function to stop all services
function Stop-DemoServices {
    Write-Host "`nStopping all services..." -ForegroundColor Yellow
    
    # Kill all Python processes related to our demo
    Get-Process -Name "python", "python3" -ErrorAction SilentlyContinue | Where-Object { 
        $_.ProcessName -eq "python" -or $_.ProcessName -eq "python3" 
    } | ForEach-Object {
        $process = $_
        try {
            $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
            if ($cmdline -match "modbus_server|mitm_proxy|modbus_client|ui_server|defense_module") {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                Write-Host "Stopped: $cmdline" -ForegroundColor Red
            }
        } catch {
            # Ignore errors
        }
    }
    
    # Clean up PID files
    Remove-Item "pids\*.pid" -ErrorAction SilentlyContinue
    
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
        $uiRunning = $false
        if (Test-Path "pids\ui_server.pid") {
            $uiPid = Get-Content "pids\ui_server.pid" -ErrorAction SilentlyContinue
            if ($uiPid -and (Get-Process -Id $uiPid -ErrorAction SilentlyContinue)) {
                $uiRunning = $true
            }
        }
        
        if (-not $uiRunning) {
            Write-Host "UI server stopped - ending demo" -ForegroundColor Red
            break
        }
        
        # Optional: Check if other services are still running
        $pythonProcesses = Get-Process -Name "python", "python3" -ErrorAction SilentlyContinue | Where-Object { 
            $_.ProcessName -eq "python" -or $_.ProcessName -eq "python3" 
        }
        $demoProcesses = 0
        
        foreach ($process in $pythonProcesses) {
            try {
                $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
                if ($cmdline -match "modbus_server|mitm_proxy|modbus_client|ui_server") {
                    $demoProcesses++
                }
            } catch {
                # Ignore errors
            }
        }
        
        if ($demoProcesses -eq 0) {
            Write-Host "All demo processes stopped - ending demo" -ForegroundColor Red
            break
        }
        
    } while ($true)
}
finally {
    Stop-DemoServices
    Unregister-Event -SourceIdentifier PowerShell.Exiting -ErrorAction SilentlyContinue
}