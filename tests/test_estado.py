import logging
from datetime import datetime, timezone

from hsf_app.metricas import MetricasEjecucion
from hsf_app.estado import EstadoIntegracion, ManejadorEventos
from hsf_app.processing import ResultadoClasificacion


def _lectura(timestamp="2026-10-13T10:00:00+00:00", **overrides):
    base = {
        "device_id": "SIM-001",
        "timestamp": timestamp,
        "temperatura_c": 22.5,
        "humedad_pct": 45.0,
        "vibracion_mm_s": 1.2,
    }
    base.update(overrides)
    return base


def test_snapshot_inicial_sin_datos():
    snapshot = EstadoIntegracion().snapshot()

    assert snapshot["conexion"] == "iniciando"
    assert snapshot["lecturas"] == []
    assert snapshot["ultima"] is None
    assert snapshot["indicadores"]["disponibilidad_pct"] is None


def test_al_procesar_guarda_la_lectura_con_su_latencia():
    estado = EstadoIntegracion()
    ahora = datetime(2026, 10, 13, 10, 0, 0, 250000, tzinfo=timezone.utc)

    estado.al_procesar(_lectura(), ResultadoClasificacion("anomalo", ["vibracion_mm_s"]), ahora=ahora)

    ultima = estado.snapshot()["ultima"]
    assert ultima["latencia_ms"] == 250.0
    assert ultima["estado"] == "anomalo"
    assert ultima["variables_anomalas"] == ["vibracion_mm_s"]


def test_timestamp_ilegible_deja_la_latencia_vacia():
    estado = EstadoIntegracion()

    estado.al_procesar(_lectura(timestamp="no-es-fecha"), ResultadoClasificacion("normal", []))

    assert estado.snapshot()["ultima"]["latencia_ms"] is None


def test_timestamp_sin_zona_horaria_deja_la_latencia_vacia():
    estado = EstadoIntegracion()

    estado.al_procesar(_lectura(timestamp="2026-10-13T10:00:00"), ResultadoClasificacion("normal", []))

    assert estado.snapshot()["ultima"]["latencia_ms"] is None


def test_el_buffer_de_lecturas_tiene_tope():
    estado = EstadoIntegracion(max_lecturas=3)
    for _ in range(5):
        estado.al_procesar(_lectura(), ResultadoClasificacion("normal", []))

    assert len(estado.snapshot()["lecturas"]) == 3


def test_transiciones_de_conexion():
    estado = EstadoIntegracion()

    estado.al_conectar()
    assert estado.snapshot()["conexion"] == "conectado"
    estado.al_desconectar()
    assert estado.snapshot()["conexion"] == "reconectando"
    estado.al_rendirse()
    assert estado.snapshot()["conexion"] == "desconectado"
    estado.al_finalizar()
    assert estado.snapshot()["conexion"] == "detenido"


def test_indicadores_se_calculan_desde_las_metricas_vinculadas():
    estado = EstadoIntegracion()
    estado.al_iniciar(MetricasEjecucion(lecturas_recibidas=40, lecturas_validas=40, desconexiones=1))

    snapshot = estado.snapshot()

    assert snapshot["indicadores"]["disponibilidad_pct"] == 97.6
    assert snapshot["indicadores"]["datos_validos_pct"] == 100.0
    assert snapshot["metricas"]["lecturas_validas"] == 40


def test_manejador_de_eventos_lleva_los_logs_al_estado():
    estado = EstadoIntegracion()
    logger = logging.getLogger("test-eventos-dashboard")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(ManejadorEventos(estado))

    logger.warning("lectura anómala de SIM-001")

    evento = estado.snapshot()["eventos"][-1]
    assert evento["nivel"] == "WARNING"
    assert "anómala" in evento["mensaje"]
