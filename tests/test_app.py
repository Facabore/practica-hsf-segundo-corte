import json
import logging

from hsf_app.acquisition import ErrorAdquisicion
from hsf_app.app import OrquestadorHSF
from hsf_app.validation import ErrorValidacion


def _lectura(**overrides):
    base = {
        "device_id": "SIM-001",
        "timestamp": "2026-10-06T10:00:00",
        "temperatura_c": 22.5,
        "humedad_pct": 45.0,
        "vibracion_mm_s": 1.2,
    }
    base.update(overrides)
    return base


class FuenteFalsa:
    """Doble de prueba de FuenteAdquisicion: no usa sockets reales."""

    def __init__(self, eventos):
        self._eventos = list(eventos)
        self.intentos_conexion = 0
        self.conectar_con_reintentos_resultado = True

    def conectar_con_reintentos(self, en_cada_intento=None):
        self.intentos_conexion += 1
        return self.conectar_con_reintentos_resultado

    def leer_siguiente(self):
        if not self._eventos:
            raise ConnectionError("fin de eventos de prueba")
        evento = self._eventos.pop(0)
        if isinstance(evento, Exception):
            raise evento
        return evento


def _logger_silencioso():
    logger = logging.getLogger("test-hsf")
    logger.addHandler(logging.NullHandler())
    return logger


def test_ejecutar_procesa_lecturas_validas_y_genera_reporte(tmp_path):
    ruta_csv = tmp_path / "lecturas.csv"
    ruta_reporte = tmp_path / "reporte.json"
    fuente = FuenteFalsa([_lectura(), _lectura(temperatura_c=60.0), _lectura()])

    orquestador = OrquestadorHSF(
        fuente=fuente,
        logger=_logger_silencioso(),
        ruta_csv=ruta_csv,
        ruta_reporte=ruta_reporte,
        max_lecturas=3,
    )
    metricas = orquestador.ejecutar()

    assert metricas.lecturas_validas == 3
    assert metricas.lecturas_anomalas == 1
    assert ruta_csv.exists()
    assert ruta_reporte.exists()

    reporte = json.loads(ruta_reporte.read_text(encoding="utf-8"))
    assert reporte["lecturas_validas"] == 3


def test_ejecutar_cuenta_errores_de_validacion_sin_detenerse(tmp_path):
    lectura_invalida = _lectura()
    del lectura_invalida["humedad_pct"]
    fuente = FuenteFalsa([lectura_invalida, _lectura()])

    orquestador = OrquestadorHSF(
        fuente=fuente,
        logger=_logger_silencioso(),
        ruta_csv=tmp_path / "lecturas.csv",
        ruta_reporte=tmp_path / "reporte.json",
        max_lecturas=2,
    )
    metricas = orquestador.ejecutar()

    assert metricas.errores_validacion == 1
    assert metricas.lecturas_validas == 1


def test_ejecutar_cuenta_errores_de_adquisicion_sin_detenerse(tmp_path):
    fuente = FuenteFalsa([ErrorAdquisicion("línea corrupta"), _lectura()])

    orquestador = OrquestadorHSF(
        fuente=fuente,
        logger=_logger_silencioso(),
        ruta_csv=tmp_path / "lecturas.csv",
        ruta_reporte=tmp_path / "reporte.json",
        max_lecturas=1,
    )
    metricas = orquestador.ejecutar()

    assert metricas.errores_adquisicion == 1
    assert metricas.lecturas_validas == 1


def test_ejecutar_reconecta_tras_una_desconexion(tmp_path):
    fuente = FuenteFalsa([ConnectionError("se cayó el enlace"), _lectura()])

    orquestador = OrquestadorHSF(
        fuente=fuente,
        logger=_logger_silencioso(),
        ruta_csv=tmp_path / "lecturas.csv",
        ruta_reporte=tmp_path / "reporte.json",
        max_lecturas=1,
    )
    metricas = orquestador.ejecutar()

    assert metricas.desconexiones == 1
    assert fuente.intentos_conexion == 2  # conexión inicial + reconexión
    assert len(metricas.tiempos_recuperacion_s) == 1
    assert metricas.lecturas_validas == 1


def test_ejecutar_continua_si_falla_la_persistencia(tmp_path, monkeypatch):
    import hsf_app.app as app_module

    def falla_persistencia(*args, **kwargs):
        raise OSError("ruta sin permisos")

    monkeypatch.setattr(app_module, "registrar_lectura_csv", falla_persistencia)

    fuente = FuenteFalsa([_lectura(), _lectura()])
    orquestador = OrquestadorHSF(
        fuente=fuente,
        logger=_logger_silencioso(),
        ruta_csv=tmp_path / "lecturas.csv",
        ruta_reporte=tmp_path / "reporte.json",
        max_lecturas=2,
    )
    metricas = orquestador.ejecutar()  # no debe lanzar la excepción

    assert metricas.errores_persistencia == 2
    assert metricas.lecturas_validas == 2


def test_ejecutar_no_crashea_si_no_logra_conectar_nunca(tmp_path):
    fuente = FuenteFalsa([])
    fuente.conectar_con_reintentos_resultado = False

    orquestador = OrquestadorHSF(
        fuente=fuente,
        logger=_logger_silencioso(),
        ruta_csv=tmp_path / "lecturas.csv",
        ruta_reporte=tmp_path / "reporte.json",
        max_lecturas=5,
    )
    metricas = orquestador.ejecutar()  # no debe lanzar excepción

    assert metricas.lecturas_recibidas == 0
    assert (tmp_path / "reporte.json").exists()
