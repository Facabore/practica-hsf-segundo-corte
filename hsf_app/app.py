"""Orquestador principal: conecta, adquiere, valida, clasifica, persiste
y reporta (RF01-RF10). Es la pieza que recorre toda la cadena hardware/
firmware → sistema operativo → software → persistencia/reporte.

Separa el bucle de la fuente real de datos (`FuenteAdquisicion`) para que
se pueda probar con un doble de prueba sin abrir sockets (ver
`tests/test_app.py`), y nunca deja que una falla de comunicación o un
dato inválido detenga la aplicación (RF09): cada tipo de error se cuenta
y se registra, y el ciclo continúa.
"""

import threading
import time

from hsf_app.acquisition import ErrorAdquisicion, FuenteAdquisicion
from hsf_app.config import LECTURAS_CSV_PATH, REPORTE_JSON_PATH
from hsf_app.estado import EstadoIntegracion
from hsf_app.metricas import MetricasEjecucion
from hsf_app.os_resources import obtener_snapshot_recursos
from hsf_app.persistence import generar_reporte_json, registrar_lectura_csv
from hsf_app.processing import clasificar_lectura
from hsf_app.validation import ErrorValidacion, validar_lectura


class OrquestadorHSF:
    def __init__(
        self,
        fuente,
        logger,
        ruta_csv=LECTURAS_CSV_PATH,
        ruta_reporte=REPORTE_JSON_PATH,
        max_lecturas=None,
        estado: EstadoIntegracion | None = None,
        reintentar_siempre: bool = False,
    ):
        self.fuente = fuente
        self.logger = logger
        self.ruta_csv = ruta_csv
        self.ruta_reporte = ruta_reporte
        self.max_lecturas = max_lecturas
        self.estado = estado or EstadoIntegracion()
        # En la demo en vivo, si se detiene el firmware desde el dashboard, la
        # app debe seguir esperándolo en vez de rendirse tras el backoff.
        self.reintentar_siempre = reintentar_siempre
        self._detener = threading.Event()

    def detener(self) -> None:
        """Pide terminar el ciclo; seguro de llamar desde otro hilo."""
        self._detener.set()
        if hasattr(self.fuente, "cerrar"):
            self.fuente.cerrar()

    def _log_intento_reconexion(self, espera, excepcion):
        self.logger.warning("reintentando conexión con el firmware (espera=%ss): %s", espera, excepcion)

    def _conectar(self) -> bool:
        while not self._detener.is_set():
            if self.fuente.conectar_con_reintentos(self._log_intento_reconexion, cancelado=self._detener):
                return True
            if not self.reintentar_siempre:
                return False
            self.logger.warning("el firmware sigue sin responder; se continúa intentando")
        return False

    def _debe_seguir(self, metricas: MetricasEjecucion) -> bool:
        if self._detener.is_set():
            return False
        return self.max_lecturas is None or metricas.lecturas_validas + metricas.errores_validacion < self.max_lecturas

    def ejecutar(self) -> MetricasEjecucion:
        metricas = MetricasEjecucion()
        self.estado.al_iniciar(metricas)

        if not self._conectar():
            self.logger.error("no fue posible conectar con el firmware, se detiene la adquisición")
            self.estado.al_rendirse()
            metricas.tiempo_fin_s = time.time()
            generar_reporte_json(self.ruta_reporte, metricas.resumen())
            return metricas

        self.estado.al_conectar()
        self.logger.info("integración activa: conectado al firmware")
        rendido = False

        try:
            while self._debe_seguir(metricas):
                try:
                    lectura_cruda = self.fuente.leer_siguiente()
                except ErrorAdquisicion as exc:
                    metricas.errores_adquisicion += 1
                    self.logger.warning("dato descartado por error de adquisición: %s", exc)
                    continue
                except OSError as exc:  # ConnectionError y cualquier otra falla del socket
                    if self._detener.is_set():
                        break
                    metricas.desconexiones += 1
                    self.estado.al_desconectar()
                    self.logger.error("se perdió la conexión con el firmware: %s", exc)
                    inicio_caida = time.time()
                    if not self._conectar():
                        if not self._detener.is_set():
                            rendido = True
                            self.estado.al_rendirse()
                            self.logger.error("no se pudo recuperar la conexión, se detiene la adquisición")
                        break
                    metricas.tiempos_recuperacion_s.append(round(time.time() - inicio_caida, 2))
                    self.estado.al_conectar()
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
                self.estado.al_procesar(lectura_cruda, clasificacion)

                try:
                    registrar_lectura_csv(self.ruta_csv, lectura_cruda, clasificacion.estado)
                except OSError as exc:
                    metricas.errores_persistencia += 1
                    self.logger.error("no se pudo persistir la lectura (ruta inaccesible): %s", exc)
        except KeyboardInterrupt:
            self.logger.info("detenido por el usuario (Ctrl+C), generando reporte final")
        finally:
            self.fuente.cerrar() if hasattr(self.fuente, "cerrar") else None
            if not rendido:
                self.estado.al_finalizar()
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
