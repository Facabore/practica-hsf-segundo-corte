"""Orquestador principal: conecta, adquiere, valida, clasifica, persiste
y reporta (RF01-RF10). Es la pieza que recorre toda la cadena hardware/
firmware → sistema operativo → software → persistencia/reporte.

Separa el bucle de la fuente real de datos (`FuenteAdquisicion`) para que
se pueda probar con un doble de prueba sin abrir sockets (ver
`tests/test_app.py`), y nunca deja que una falla de comunicación o un
dato inválido detenga la aplicación (RF09): cada tipo de error se cuenta
y se registra, y el ciclo continúa.
"""

import time
from dataclasses import dataclass, field

from hsf_app.acquisition import ErrorAdquisicion, FuenteAdquisicion
from hsf_app.config import LECTURAS_CSV_PATH, REPORTE_JSON_PATH
from hsf_app.os_resources import obtener_snapshot_recursos
from hsf_app.persistence import generar_reporte_json, registrar_lectura_csv
from hsf_app.processing import clasificar_lectura
from hsf_app.validation import ErrorValidacion, validar_lectura


@dataclass
class MetricasEjecucion:
    lecturas_recibidas: int = 0
    lecturas_validas: int = 0
    lecturas_anomalas: int = 0
    errores_validacion: int = 0
    errores_adquisicion: int = 0
    errores_persistencia: int = 0
    desconexiones: int = 0
    tiempos_recuperacion_s: list = field(default_factory=list)
    tiempo_inicio_s: float = field(default_factory=time.time)
    tiempo_fin_s: float = field(default_factory=time.time)

    def resumen(self) -> dict:
        total_eventos = self.lecturas_recibidas + self.errores_adquisicion
        datos_validos_pct = (
            round(100 * self.lecturas_validas / self.lecturas_recibidas, 2)
            if self.lecturas_recibidas
            else 0.0
        )
        errores_totales = self.errores_validacion + self.errores_adquisicion + self.errores_persistencia
        tasa_errores_pct = (
            round(100 * errores_totales / total_eventos, 2) if total_eventos else 0.0
        )
        tiempo_recuperacion_promedio_s = (
            round(sum(self.tiempos_recuperacion_s) / len(self.tiempos_recuperacion_s), 2)
            if self.tiempos_recuperacion_s
            else 0.0
        )
        return {
            "lecturas_recibidas": self.lecturas_recibidas,
            "lecturas_validas": self.lecturas_validas,
            "lecturas_anomalas": self.lecturas_anomalas,
            "errores_validacion": self.errores_validacion,
            "errores_adquisicion": self.errores_adquisicion,
            "errores_persistencia": self.errores_persistencia,
            "desconexiones": self.desconexiones,
            "datos_validos_pct": datos_validos_pct,
            "tasa_errores_pct": tasa_errores_pct,
            "tiempo_recuperacion_promedio_s": tiempo_recuperacion_promedio_s,
            "duracion_total_s": round(self.tiempo_fin_s - self.tiempo_inicio_s, 2),
        }


class OrquestadorHSF:
    def __init__(self, fuente, logger, ruta_csv=LECTURAS_CSV_PATH, ruta_reporte=REPORTE_JSON_PATH, max_lecturas=None):
        self.fuente = fuente
        self.logger = logger
        self.ruta_csv = ruta_csv
        self.ruta_reporte = ruta_reporte
        self.max_lecturas = max_lecturas

    def _log_intento_reconexion(self, espera, excepcion):
        self.logger.warning("reintentando conexión con el firmware (espera=%ss): %s", espera, excepcion)

    def ejecutar(self) -> MetricasEjecucion:
        metricas = MetricasEjecucion()

        if not self.fuente.conectar_con_reintentos(self._log_intento_reconexion):
            self.logger.error("no fue posible conectar con el firmware, se detiene la adquisición")
            metricas.tiempo_fin_s = time.time()
            generar_reporte_json(self.ruta_reporte, metricas.resumen())
            return metricas

        self.logger.info("integración activa: conectado al firmware")

        try:
            while self.max_lecturas is None or metricas.lecturas_validas + metricas.errores_validacion < self.max_lecturas:
                try:
                    lectura_cruda = self.fuente.leer_siguiente()
                except ErrorAdquisicion as exc:
                    metricas.errores_adquisicion += 1
                    self.logger.warning("dato descartado por error de adquisición: %s", exc)
                    continue
                except ConnectionError as exc:
                    metricas.desconexiones += 1
                    self.logger.error("se perdió la conexión con el firmware: %s", exc)
                    inicio_caida = time.time()
                    if not self.fuente.conectar_con_reintentos(self._log_intento_reconexion):
                        self.logger.error("no se pudo recuperar la conexión, se detiene la adquisición")
                        break
                    metricas.tiempos_recuperacion_s.append(round(time.time() - inicio_caida, 2))
                    self.logger.info("conexión recuperada con el firmware")
                    continue

                metricas.lecturas_recibidas += 1

                try:
                    validar_lectura(lectura_cruda)
                except ErrorValidacion as exc:
                    metricas.errores_validacion += 1
                    self.logger.warning("lectura descartada por validación: %s", exc)
                    continue

                metricas.lecturas_validas += 1
                clasificacion = clasificar_lectura(lectura_cruda)
                if clasificacion.estado == "anomalo":
                    metricas.lecturas_anomalas += 1
                    self.logger.warning(
                        "lectura anómala de %s: variables=%s",
                        lectura_cruda.get("device_id"),
                        clasificacion.variables_anomalas,
                    )
                else:
                    self.logger.info("lectura normal de %s procesada", lectura_cruda.get("device_id"))

                try:
                    registrar_lectura_csv(self.ruta_csv, lectura_cruda, clasificacion.estado)
                except OSError as exc:
                    metricas.errores_persistencia += 1
                    self.logger.error("no se pudo persistir la lectura (ruta inaccesible): %s", exc)
        except KeyboardInterrupt:
            self.logger.info("detenido por el usuario (Ctrl+C), generando reporte final")
        finally:
            self.fuente.cerrar() if hasattr(self.fuente, "cerrar") else None
            metricas.tiempo_fin_s = time.time()
            snapshot_recursos = obtener_snapshot_recursos()
            resumen = metricas.resumen()
            resumen["recursos_sistema_operativo"] = snapshot_recursos
            try:
                generar_reporte_json(self.ruta_reporte, resumen)
            except OSError as exc:
                self.logger.error("no se pudo escribir el reporte final: %s", exc)

        return metricas


def main() -> None:  # pragma: no cover - punto de entrada manual
    from hsf_app.logging_setup import configurar_logging

    logger = configurar_logging()
    fuente = FuenteAdquisicion()
    orquestador = OrquestadorHSF(fuente=fuente, logger=logger)
    metricas = orquestador.ejecutar()
    print(f"[ESTADO] integración finalizada — {metricas.resumen()}")


if __name__ == "__main__":
    main()
