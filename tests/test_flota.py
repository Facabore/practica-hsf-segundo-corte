import logging

from hsf_app.config import Dispositivo
from hsf_app.estado import EstadoIntegracion, ManejadorEventos
from hsf_app.flota import EstadoFlota, LoggerDispositivo
from hsf_app.metricas import MetricasEjecucion
from hsf_app.processing import ResultadoClasificacion

COMPRESOR = Dispositivo("SIM-001", "Compresor", 8765, 7)
BOMBA = Dispositivo("SIM-002", "Bomba de agua", 8766, 11)


def _flota():
    estados = {COMPRESOR.id: EstadoIntegracion(), BOMBA.id: EstadoIntegracion()}
    flota = EstadoFlota([(COMPRESOR, estados[COMPRESOR.id]), (BOMBA, estados[BOMBA.id])])
    return flota, estados


def test_el_snapshot_trae_cada_dispositivo_con_su_identidad():
    flota, estados = _flota()
    estados[BOMBA.id].al_procesar(
        {"device_id": "SIM-002", "timestamp": "2026-10-14T10:00:00+00:00", "temperatura_c": 20.0, "humedad_pct": 40.0, "vibracion_mm_s": 1.0},
        ResultadoClasificacion("normal", []),
    )

    equipos = flota.snapshot()["dispositivos"]

    assert [e["id"] for e in equipos] == ["SIM-001", "SIM-002"]
    assert equipos[1]["nombre"] == "Bomba de agua"
    assert equipos[1]["ultima"]["temperatura_c"] == 20.0
    assert "eventos" not in equipos[1]


def test_la_vista_general_suma_las_metricas_de_todos():
    flota, estados = _flota()
    estados[COMPRESOR.id].al_iniciar(MetricasEjecucion(lecturas_recibidas=10, lecturas_validas=10, lecturas_anomalas=1))
    estados[BOMBA.id].al_iniciar(MetricasEjecucion(
        lecturas_recibidas=20, lecturas_validas=18, errores_validacion=2, desconexiones=1, tiempos_recuperacion_s=[3.0],
    ))

    general = flota.snapshot()["general"]

    assert general["metricas"]["lecturas_recibidas"] == 30
    assert general["metricas"]["lecturas_anomalas"] == 1
    assert general["metricas"]["datos_validos_pct"] == 93.33
    assert general["indicadores"]["disponibilidad_pct"] == 96.8
    assert general["indicadores"]["tiempo_recuperacion_promedio_s"] == 3.0


def test_la_vista_general_cuenta_solo_los_conectados():
    flota, estados = _flota()
    estados[COMPRESOR.id].al_conectar()
    estados[BOMBA.id].al_desconectar()

    general = flota.snapshot()["general"]

    assert general["conectados"] == 1
    assert general["total"] == 2


def test_sin_metricas_todavia_los_indicadores_quedan_vacios():
    flota, _ = _flota()

    general = flota.snapshot()["general"]

    assert general["metricas"] is None
    assert general["indicadores"]["disponibilidad_pct"] is None


def test_los_eventos_de_la_flota_llevan_el_prefijo_del_dispositivo():
    flota, _ = _flota()
    logger = logging.getLogger("test-flota-eventos")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(ManejadorEventos(flota))

    LoggerDispositivo(logger, {"id": "SIM-002"}).warning("se perdió la conexión con el firmware")

    assert flota.snapshot()["eventos"][-1]["mensaje"] == "[SIM-002] se perdió la conexión con el firmware"
