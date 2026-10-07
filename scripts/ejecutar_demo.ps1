# Levanta el firmware simulado y la aplicacion Python juntos (demo manual).
# Uso: powershell -File scripts/ejecutar_demo.ps1
# Detener con Ctrl+C: la app genera el reporte final antes de salir.

$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$firmware = Start-Process -FilePath python -ArgumentList "firmware/firmware_simulador.py" -PassThru -NoNewWindow
Start-Sleep -Seconds 1

try {
    python -m hsf_app.app
}
finally {
    Stop-Process -Id $firmware.Id -ErrorAction SilentlyContinue
}
