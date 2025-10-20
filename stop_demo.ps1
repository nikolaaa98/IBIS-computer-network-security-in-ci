# Zaustavi IBIS Demo - Windows
Write-Host "🛑 Zaustavljam IBIS Demo..." -ForegroundColor Yellow

Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -match "modbus_server|mitm_proxy|modbus_client|ui_server|defense_module" } | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2
Write-Host "✅ Svi procesi zaustavljeni" -ForegroundColor Green