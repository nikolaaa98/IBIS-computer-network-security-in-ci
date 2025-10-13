$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PidDir = Join-Path $RootDir "pids"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Stopping Modbus Services" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $PidDir)) {
    Write-Host "No PID directory found. Services may not be running." -ForegroundColor Yellow
    exit 0
}

$services = @("modbus_client", "modbus_proxy", "modbus_server")
$stoppedCount = 0

foreach ($serviceName in $services) {
    $pidFile = Join-Path $PidDir ("{0}.pid" -f $serviceName)
    
    if (Test-Path $pidFile) {
        $pid = Get-Content $pidFile -Raw
        $pid = $pid.Trim()
        
        Write-Host "Stopping $serviceName (PID: $pid)..." -ForegroundColor Yellow
        
        try {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            
            if ($process) {
                Stop-Process -Id $pid -Force
                Start-Sleep -Milliseconds 500
                
                # Verify it stopped
                $checkProcess = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($checkProcess) {
                    Write-Host "  └─ WARNING: Process may still be running" -ForegroundColor Yellow
                } else {
                    Write-Host "  └─ Stopped successfully" -ForegroundColor Green
                    $stoppedCount++
                }
            } else {
                Write-Host "  └─ Process not found (already stopped)" -ForegroundColor Gray
            }
            
            # Remove PID file
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
            
        } catch {
            Write-Host "  └─ Error stopping process: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "$serviceName - no PID file found" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Stopped $stoppedCount service(s)" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
