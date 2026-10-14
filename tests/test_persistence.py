import csv
import json

import io

from hsf_app.persistence import COLUMNAS_REPORTE_CSV, generar_reporte_json, registrar_lectura_csv, reporte_a_csv


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


def test_registrar_lectura_csv_crea_archivo_con_encabezado(tmp_path):
    ruta = tmp_path / "lecturas.csv"
    registrar_lectura_csv(ruta, _lectura(), estado="normal")

    with ruta.open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))

    assert len(filas) == 1
    assert filas[0]["device_id"] == "SIM-001"
    assert filas[0]["estado"] == "normal"


def test_registrar_lectura_csv_agrega_filas_sin_duplicar_encabezado(tmp_path):
    ruta = tmp_path / "lecturas.csv"
    registrar_lectura_csv(ruta, _lectura(), estado="normal")
    registrar_lectura_csv(ruta, _lectura(temperatura_c=60.0), estado="anomalo")

    with ruta.open(encoding="utf-8") as archivo:
        lineas = archivo.readlines()
        filas = list(csv.reader(lineas))

    assert filas[0][0] in ("timestamp", "device_id")
    assert len(filas) == 3  # encabezado + 2 filas de datos


def test_generar_reporte_json_escribe_metricas(tmp_path):
    ruta = tmp_path / "reporte.json"
    metricas = {
        "disponibilidad_comunicacion_pct": 96.5,
        "latencia_promedio_ms": 12.3,
        "datos_validos_pct": 98.1,
        "tasa_errores_pct": 1.9,
        "tiempo_recuperacion_s": 2.4,
    }
    generar_reporte_json(ruta, metricas)

    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    assert contenido == metricas


def _reporte():
    metricas = {"lecturas_recibidas": 10, "lecturas_validas": 9, "lecturas_anomalas": 2, "errores_validacion": 1,
                "errores_adquisicion": 0, "errores_persistencia": 0, "desconexiones": 1, "datos_validos_pct": 90.0,
                "tasa_errores_pct": 10.0, "tiempo_recuperacion_promedio_s": 1.01}
    indicadores = {"disponibilidad_pct": 90.91, "latencia_promedio_ms": 0.8, "datos_validos_pct": 90.0,
                   "tasa_errores_pct": 10.0, "tiempo_recuperacion_promedio_s": 1.01}
    return {
        "generado": "2026-10-14T07:00:00+00:00",
        "general": {"conectados": 1, "total": 2, "metricas": metricas, "indicadores": indicadores},
        "dispositivos": [
            {"id": "SIM-001", "nombre": "Compresor", "conexion": "conectado", "metricas": metricas, "indicadores": indicadores},
            {"id": "SIM-002", "nombre": "Bomba de agua", "conexion": "reconectando", "metricas": None,
             "indicadores": dict.fromkeys(indicadores)},
        ],
        "recursos_sistema_operativo": {"cpu_percent": 12.5, "memoria_percent": 40.0, "disco_percent": 13.0},
    }


def test_reporte_a_csv_trae_una_fila_general_y_una_por_equipo():
    filas = list(csv.DictReader(io.StringIO(reporte_a_csv(_reporte()))))

    assert [f["equipo"] for f in filas] == ["GENERAL", "SIM-001", "SIM-002"]
    assert list(filas[0]) == COLUMNAS_REPORTE_CSV
    assert filas[0]["conexion"] == "1 de 2 conectados"
    assert filas[1]["lecturas_validas"] == "9"
    assert filas[1]["disponibilidad_pct"] == "90.91"
    assert filas[1]["cpu_percent"] == "12.5"
    assert filas[2]["generado"] == "2026-10-14T07:00:00+00:00"


def test_reporte_a_csv_deja_vacio_lo_que_un_equipo_aun_no_tiene():
    sin_datos = list(csv.DictReader(io.StringIO(reporte_a_csv(_reporte()))))[2]

    assert sin_datos["conexion"] == "reconectando"
    assert sin_datos["lecturas_recibidas"] == ""
    assert sin_datos["latencia_promedio_ms"] == ""
