"""Configuración centralizada de la aplicación HSF."""

from dataclasses import dataclass
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

# La demo en vivo escribe en archivos propios (data/demo_*, logs/demo.log)
# para no alterar la evidencia documentada.
DEMO_LOG_PATH = LOG_DIR / "demo.log"
DEMO_REPORTE_GENERAL_PATH = DATA_DIR / "demo_reporte_general.json"
DASHBOARD_PORT = 8080


@dataclass(frozen=True)
class Dispositivo:
    id: str
    nombre: str
    puerto: int
    ciclos_anomalia: int


# Equipos simulados de la demo: cada uno es un proceso de firmware aparte.
# Ritmos de anomalía distintos (primos) para que sus gráficas no coincidan.
DISPOSITIVOS_DEMO = (
    Dispositivo("SIM-001", "Compresor", 8765, 7),
    Dispositivo("SIM-002", "Bomba de agua", 8766, 11),
    Dispositivo("SIM-003", "Motor de banda", 8767, 13),
)

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
