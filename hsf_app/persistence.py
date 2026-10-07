"""Persistencia de lecturas en CSV y del reporte resumen en JSON (RF07, RF08)."""

import csv
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


def generar_reporte_json(ruta: Path, metricas: dict) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
