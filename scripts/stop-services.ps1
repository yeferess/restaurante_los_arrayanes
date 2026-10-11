# Detiene los servicios del servidor lanzados por las tareas programadas.
# Stop-ScheduledTask (o "Finalizar") solo cierra wscript.exe y deja vivos
# daphne/node/caddy, por eso aqui se cierra el arbol de procesos completo
# y, como respaldo, lo que siga escuchando en el puerto del servicio.
#
# Uso: stop-services.bat [backend|frontend|caddy|all]   (por defecto: all)
param(
    [ValidateSet('backend', 'frontend', 'caddy', 'all')]
    [string]$Service = 'all'
)

$services = @{
    backend  = @{ Task = 'LosArrayanes-Backend';  Bat = 'start-backend.bat';  Port = 8000 }
    frontend = @{ Task = 'LosArrayanes-Frontend'; Bat = 'start-frontend.bat'; Port = 3000 }
    caddy    = @{ Task = 'LosArrayanes-Caddy';    Bat = 'start-caddy.bat';    Port = 443 }
}

function Stop-ProcessTree([int]$ProcessId) {
    Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" |
        ForEach-Object { Stop-ProcessTree $_.ProcessId }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

$names = if ($Service -eq 'all') { 'caddy', 'frontend', 'backend' } else { @($Service) }

foreach ($name in $names) {
    $svc = $services[$name]

    # 1. Arbol que cuelga del lanzador oculto de este servicio.
    Get-CimInstance Win32_Process -Filter "Name = 'wscript.exe'" |
        Where-Object { $_.CommandLine -like "*run-hidden.vbs*$($svc.Bat)*" } |
        ForEach-Object { Stop-ProcessTree $_.ProcessId }

    # 2. Respaldo: procesos huerfanos que sigan escuchando en el puerto.
    Get-NetTCPConnection -LocalPort $svc.Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        Where-Object { $_ -gt 4 } |
        ForEach-Object { Stop-ProcessTree $_ }

    try { Stop-ScheduledTask -TaskName $svc.Task -ErrorAction Stop } catch {}

    Start-Sleep -Milliseconds 500
    $still = Get-NetTCPConnection -LocalPort $svc.Port -State Listen -ErrorAction SilentlyContinue
    if ($still) { Write-Host "$name : el puerto $($svc.Port) sigue ocupado" -ForegroundColor Red }
    else { Write-Host "$name : detenido (puerto $($svc.Port) libre)" -ForegroundColor Green }
}

Write-Host "Para volver a arrancar: Start-ScheduledTask -TaskName <tarea>, o 'Ejecutar' en el Programador de tareas."
