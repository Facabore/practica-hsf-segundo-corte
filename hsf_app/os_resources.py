"""Consulta de recursos del sistema operativo (RF06, Fase 5).

Usa `psutil` cuando está disponible (CPU, memoria, disco, proceso propio).
Si no está instalado, cae a `os`/`platform`, que siempre están disponibles
en la librería estándar — así el módulo nunca rompe por falta de una
dependencia opcional (requisito de confiabilidad).
"""

import os
import platform
import threading

try:
    import psutil
except ImportError:  # pragma: no cover - depende del entorno
    psutil = None

VARIABLES_ENTORNO_RELEVANTES = ("PATH", "PYTHONPATH", "OS", "USERNAME", "USER")
# Variables cuyo valor es una lista de rutas del equipo local: se resumen
# (cantidad de entradas) en vez de volcarse completas, para no filtrar la
# estructura de carpetas ni el software instalado en la máquina.
VARIABLES_TIPO_RUTA = ("PATH", "PYTHONPATH")


def _variables_entorno_relevantes() -> dict:
    variables = {}
    for nombre in VARIABLES_ENTORNO_RELEVANTES:
        valor = os.environ.get(nombre)
        if valor is None:
            continue
        if nombre in VARIABLES_TIPO_RUTA:
            cantidad = len([p for p in valor.split(os.pathsep) if p])
            valor = f"({cantidad} entradas, valor omitido por privacidad)"
        variables[nombre] = valor
    return variables


def obtener_snapshot_recursos() -> dict:
    snapshot = {
        "sistema_operativo": platform.system(),
        "version_os": platform.version(),
        "proceso_pid": os.getpid(),
        "variables_entorno_relevantes": _variables_entorno_relevantes(),
    }

    if psutil is None:
        snapshot.update(
            {
                "cpu_percent": None,
                "memoria_percent": None,
                "memoria_disponible_bytes": None,
                "disco_percent": None,
                "disco_libre_bytes": None,
                "memoria_proceso_bytes": None,
                "fuente": "fallback-os-platform",
            }
        )
        return snapshot

    disco = psutil.disk_usage(os.sep)
    proceso = psutil.Process()
    snapshot.update(
        {
            "cpu_percent": psutil.cpu_percent(),
            "memoria_percent": psutil.virtual_memory().percent,
            "memoria_disponible_bytes": psutil.virtual_memory().available,
            "disco_percent": disco.percent,
            "disco_libre_bytes": disco.free,
            "proceso_pid": proceso.pid,
            "memoria_proceso_bytes": proceso.memory_info().rss,
            "fuente": "psutil",
        }
    )
    return snapshot


class MuestreadorCPU:
    """Mide el uso de CPU siempre desde un mismo hilo dedicado.

    psutil.cpu_percent() recuerda la medición anterior por hilo: un servidor
    que atiende cada petición en un hilo nuevo recibiría siempre 0.0.
    """

    def __init__(self, intervalo: float = 1.0):
        self.intervalo = intervalo
        self.ultimo: float | None = None
        self._detener = threading.Event()
        self._hilo: threading.Thread | None = None

    def iniciar(self) -> None:
        self._hilo = threading.Thread(target=self._medir, name="muestreador-cpu", daemon=True)
        self._hilo.start()

    def _medir(self) -> None:
        while not self._detener.is_set():
            if psutil is None:
                return
            self.ultimo = psutil.cpu_percent(interval=self.intervalo)

    def detener(self) -> None:
        self._detener.set()
        if self._hilo is not None:
            self._hilo.join(timeout=self.intervalo + 1)
