"""Configuración centralizada de la aplicación HSF."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Comunicación con el firmware simulado
FIRMWARE_HOST = "127.0.0.1"
FIRMWARE_PORT = 8765
RECONNECT_BACKOFF_SECONDS = (1, 2, 4, 8)
SOCKET_TIMEOUT_SECONDS = 5

# Rutas de persistencia y logs
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
LECTURAS_CSV_PATH = DATA_DIR / "lecturas.csv"
REPORTE_JSON_PATH = DATA_DIR / "reporte_ejecucion.json"
LOG_FILE_PATH = LOG_DIR / "sistema.log"

# Umbrales de clasificación normal / anómalo
RANGOS_NORMALES = {
    "temperatura_c": (10.0, 45.0),
    "humedad_pct": (10.0, 90.0),
    "vibracion_mm_s": (0.0, 5.0),
}

# Rango físicamente aceptable (fuera de esto, el dato se descarta como inválido)
RANGOS_VALIDOS = {
    "temperatura_c": (-40.0, 125.0),
    "humedad_pct": (0.0, 100.0),
    "vibracion_mm_s": (0.0, 50.0),
}

CAMPOS_REQUERIDOS = {
    "device_id": str,
    "timestamp": str,
    "temperatura_c": (int, float),
    "humedad_pct": (int, float),
    "vibracion_mm_s": (int, float),
}
