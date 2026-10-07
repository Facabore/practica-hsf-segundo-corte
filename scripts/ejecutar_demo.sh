#!/usr/bin/env bash
# Levanta el firmware simulado y la aplicación Python juntos (demo manual).
# Uso: bash scripts/ejecutar_demo.sh
# Detener con Ctrl+C: la app genera el reporte final antes de salir.
set -euo pipefail
cd "$(dirname "$0")/.."

python firmware/firmware_simulador.py &
FIRMWARE_PID=$!
trap 'kill $FIRMWARE_PID 2>/dev/null || true' EXIT

sleep 1
python -m hsf_app.app
