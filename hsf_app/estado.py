"""Estado en vivo de la integración, compartido entre el orquestador (que lo
escribe) y el dashboard (que lo lee desde otro hilo).

El orquestador no sabe nada de HTTP: solo avisa a este objeto qué pasó
(se conectó, procesó una lectura, perdió el enlace). El dashboard solo
pide `snapshot()`. Así ninguna de las dos piezas depende de la otra.
"""

import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone

CAMPOS_LECTURA = ("timestamp", "temperatura_c", "humedad_pct", "vibracion_mm_s")


def calcular_latencia_ms(timestamp_iso: str, ahora: datetime) -> float | None:
    try:
        enviado = datetime.fromisoformat(timestamp_iso)
    except (TypeError, ValueError):
        return None
    if enviado.tzinfo is None:
        return None  # sin zona horaria no se puede comparar con el reloj local
    return round((ahora - enviado).total_seconds() * 1000, 3)


class EstadoIntegracion:
    def __init__(self, max_lecturas: int = 90, max_eventos: int = 40):
        self._lock = threading.Lock()
        self._lecturas = deque(maxlen=max_lecturas)
        self._eventos = deque(maxlen=max_eventos)
        self._conexion = "iniciando"
        self._metricas = None
        self._inicio = time.time()

    def al_iniciar(self, metricas) -> None:
        with self._lock:
            self._metricas = metricas
            self._conexion = "conectando"

    def al_conectar(self) -> None:
        self._cambiar_conexion("conectado")

    def al_desconectar(self) -> None:
        self._cambiar_conexion("reconectando")

    def al_rendirse(self) -> None:
        self._cambiar_conexion("desconectado")

    def al_finalizar(self) -> None:
        self._cambiar_conexion("detenido")

    def _cambiar_conexion(self, valor: str) -> None:
        with self._lock:
            self._conexion = valor

    def al_procesar(self, lectura: dict, clasificacion, ahora: datetime | None = None) -> None:
        ahora = ahora or datetime.now(timezone.utc)
        registro = {campo: lectura.get(campo) for campo in CAMPOS_LECTURA}
        registro["estado"] = clasificacion.estado
        registro["variables_anomalas"] = list(clasificacion.variables_anomalas)
        registro["latencia_ms"] = calcular_latencia_ms(lectura.get("timestamp"), ahora)
        with self._lock:
            self._lecturas.append(registro)

    def agregar_evento(self, nivel: str, mensaje: str, hora: str) -> None:
        with self._lock:
            self._eventos.append({"hora": hora, "nivel": nivel, "mensaje": mensaje})

    def snapshot(self) -> dict:
        with self._lock:
            lecturas = list(self._lecturas)
            eventos = list(self._eventos)
            conexion = self._conexion
            metricas = self._metricas.resumen() if self._metricas else None

        latencias = [l["latencia_ms"] for l in lecturas if l["latencia_ms"] is not None]
        return {
            "conexion": conexion,
            "segundos_activo": round(time.time() - self._inicio, 1),
            "lecturas": lecturas,
            "ultima": lecturas[-1] if lecturas else None,
            "eventos": eventos,
            "metricas": metricas,
            "indicadores": {
                "disponibilidad_pct": _disponibilidad(metricas),
                "latencia_promedio_ms": round(sum(latencias) / len(latencias), 3) if latencias else None,
                "datos_validos_pct": metricas["datos_validos_pct"] if metricas else None,
                "tasa_errores_pct": metricas["tasa_errores_pct"] if metricas else None,
                "tiempo_recuperacion_promedio_s": metricas["tiempo_recuperacion_promedio_s"] if metricas else None,
            },
        }


def _disponibilidad(metricas: dict | None) -> float | None:
    # Mensajes que llegaron (válidos o corruptos) sobre los esperados; cada
    # desconexión cuenta como un mensaje esperado que no llegó.
    if not metricas:
        return None
    recibidos = metricas["lecturas_recibidas"] + metricas["errores_adquisicion"]
    esperados = recibidos + metricas["desconexiones"]
    return round(100 * recibidos / esperados, 1) if esperados else None


class ManejadorEventos(logging.Handler):
    """Lleva cada línea de log al estado, para mostrarla en el dashboard."""

    def __init__(self, estado: EstadoIntegracion):
        super().__init__(level=logging.INFO)
        self.estado = estado

    def emit(self, record: logging.LogRecord) -> None:
        hora = time.strftime("%H:%M:%S", time.localtime(record.created))
        self.estado.agregar_evento(record.levelname, record.getMessage(), hora)
