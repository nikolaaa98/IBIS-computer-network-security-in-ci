# stop_demo.ps1
# Stop IBIS Demo - Windows Version

Write-Host "Stopping IBIS Demo..." -ForegroundColor Yellow

# Stop background jobs
Get-Job | Where-Object { $_.Name -like "*modbus*" -or $_.Name -like "*proxy*" } | Stop-Job -PassThru | Remove-Job -Force

# Stop processes by PID files
if (Test-Path "pids\ui_server.pid") {
    $uiPid = Get-Content "pids\ui_server.pid" -ErrorAction SilentlyContinue
    if ($uiPid) {
        Get-Process -Id $uiPid -ErrorAction SilentlyContinue | Stop-Process -Force
        Write-Host "Stopped UI server (PID: $uiPid)" -ForegroundColor Green
    }
    Remove-Item "pids\ui_server.pid" -ErrorAction SilentlyContinue
}

# Kill any remaining Python processes related to our demo
Get-Process -Name "python", "python3" -ErrorAction SilentlyContinue | Where-Object { 
    $_.ProcessName -eq "python" -or $_.ProcessName -eq "python3" 
} | ForEach-Object {
    $process = $_
    try {
        $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
        if ($cmdline -match "modbus_server|mitm_proxy|modbus_client|ui_server|defense_module") {
            Stop-Process -Id $process.Id -Force
            Write-Host "Stopped process: $cmdline" -ForegroundColor Green
        }
    } catch {
        # Ignore errors
    }
}

# Clean up PID files
Remove-Item "pids\*.pid" -ErrorAction SilentlyContinue

Write-Host "Demo stopped successfully!" -ForegroundColor Green