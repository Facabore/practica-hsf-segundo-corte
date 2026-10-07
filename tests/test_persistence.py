import csv
import json

from hsf_app.persistence import generar_reporte_json, registrar_lectura_csv


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
