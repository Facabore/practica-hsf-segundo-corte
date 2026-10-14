"""Vista de flota: varios dispositivos integrados a la vez.

Cada dispositivo tiene su propio orquestador y su propio EstadoIntegracion;
EstadoFlota solo los reúne para el dashboard y calcula la vista general
sumando sus métricas con las mismas fórmulas de MetricasEjecucion.
"""

import logging
import threading
import time
from collections import deque

from hsf_app.config import Dispositivo
from hsf_app.estado import EstadoIntegracion, calcular_indicadores
from hsf_app.metricas import MetricasEjecucion

CAMPOS_SUMABLES = (
    "lecturas_recibidas",
    "lecturas_validas",
    "lecturas_anomalas",
    "errores_validacion",
    "errores_adquisicion",
    "errores_persistencia",
    "desconexiones",
)


class LoggerDispositivo(logging.LoggerAdapter):
    """Antepone el id del dispositivo a cada línea de log: "[SIM-002] ..."."""

    def process(self, msg, kwargs):
        return f"[{self.extra['id']}] {msg}", kwargs


class EstadoFlota:
    def __init__(self, dispositivos: list[tuple[Dispositivo, EstadoIntegracion]], max_eventos: int = 80):
        self._dispositivos = list(dispositivos)
        self._lock = threading.Lock()
        self._eventos = deque(maxlen=max_eventos)
        self._inicio = time.time()

    def agregar_evento(self, nivel: str, mensaje: str, hora: str) -> None:
        with self._lock:
            self._eventos.append({"hora": hora, "nivel": nivel, "mensaje": mensaje})

    def snapshot(self) -> dict:
        equipos = []
        for dispositivo, estado in self._dispositivos:
            datos = estado.snapshot()
            datos.pop("eventos", None)  # los eventos viven en la flota, con prefijo de equipo
            equipos.append({"id": dispositivo.id, "nombre": dispositivo.nombre, "puerto": dispositivo.puerto, **datos})
        with self._lock:
            eventos = list(self._eventos)
        return {
            "segundos_activo": round(time.time() - self._inicio, 1),
            "dispositivos": equipos,
            "general": _vista_general(equipos),
            "eventos": eventos,
        }


def _vista_general(equipos: list[dict]) -> dict:
    con_metricas = [e for e in equipos if e["metricas"]]
    metricas = None
    if con_metricas:
        suma = MetricasEjecucion(
            **{campo: sum(e["metricas"][campo] for e in con_metricas) for campo in CAMPOS_SUMABLES},
            tiempos_recuperacion_s=[t for e in equipos for t in e["tiempos_recuperacion_s"]],
        )
        metricas = suma.resumen()
        metricas.pop("duracion_total_s")  # no tiene sentido sumada
    latencias = [l["latencia_ms"] for e in equipos for l in e["lecturas"] if l["latencia_ms"] is not None]
    return {
        "conectados": sum(1 for e in equipos if e["conexion"] == "conectado"),
        "total": len(equipos),
        "metricas": metricas,
        "indicadores": calcular_indicadores(metricas, latencias),
    }
