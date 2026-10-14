"""Persistencia de lecturas en CSV y del reporte resumen en JSON (RF07, RF08)."""

import csv
import io
import json
from pathlib import Path

COLUMNAS_CSV = ["timestamp", "device_id", "temperatura_c", "humedad_pct", "vibracion_mm_s", "estado"]


def registrar_lectura_csv(ruta: Path, lectura: dict, estado: str) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    existe = ruta.exists() and ruta.stat().st_size > 0

    with ruta.open("a", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_CSV)
        if not existe:
            escritor.writeheader()
        fila = {columna: lectura.get(columna) for columna in COLUMNAS_CSV[:-1]}
        fila["estado"] = estado
        escritor.writerow(fila)


CAMPOS_METRICAS = ["lecturas_recibidas", "lecturas_validas", "lecturas_anomalas", "errores_validacion",
                   "errores_adquisicion", "errores_persistencia", "desconexiones"]
CAMPOS_INDICADORES = ["disponibilidad_pct", "latencia_promedio_ms", "datos_validos_pct", "tasa_errores_pct",
                      "tiempo_recuperacion_promedio_s"]
CAMPOS_RECURSOS = ["cpu_percent", "memoria_percent", "disco_percent"]
COLUMNAS_REPORTE_CSV = ["generado", "equipo", "nombre", "conexion", *CAMPOS_METRICAS, *CAMPOS_INDICADORES, *CAMPOS_RECURSOS]


def reporte_a_csv(reporte: dict) -> str:
    """Aplana el reporte de ejecución (RF08) a una tabla: una fila GENERAL y una por equipo.

    Los recursos del SO son una sola foto del momento, así que se repiten en cada fila.
    Lo que un equipo todavía no tiene (sin lecturas, sin latencia) queda vacío.
    """
    general = reporte["general"]
    filas = [{"equipo": "GENERAL", "nombre": "Todos los equipos",
              "conexion": f"{general['conectados']} de {general['total']} conectados",
              "metricas": general["metricas"], "indicadores": general["indicadores"]}]
    filas += [{"equipo": d["id"], "nombre": d["nombre"], "conexion": d["conexion"],
               "metricas": d["metricas"], "indicadores": d["indicadores"]} for d in reporte["dispositivos"]]

    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=COLUMNAS_REPORTE_CSV, lineterminator="\n")
    escritor.writeheader()
    recursos = reporte["recursos_sistema_operativo"]
    for fila in filas:
        metricas, indicadores = fila.pop("metricas") or {}, fila.pop("indicadores") or {}
        escritor.writerow({
            "generado": reporte["generado"], **fila,
            **{campo: metricas.get(campo) for campo in CAMPOS_METRICAS},
            **{campo: indicadores.get(campo) for campo in CAMPOS_INDICADORES},
            **{campo: recursos.get(campo) for campo in CAMPOS_RECURSOS},
        })
    return salida.getvalue()


def generar_reporte_json(ruta: Path, metricas: dict) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
