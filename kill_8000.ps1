$connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($connections) {
    $pids = $connections.OwningProcess | Select-Object -Unique
    foreach ($proc_id in $pids) {
        Write-Host "Killing process $proc_id"
        Stop-Process -Id $proc_id -Force
    }
}
