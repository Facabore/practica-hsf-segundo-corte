"""Satura brevemente la CPU y toma una foto de los recursos del SO antes,
durante y después (fallo controlado "saturación de CPU o memoria", Anexo
3 §11). Usa procesos (no hilos): con hilos, el GIL de Python serializa
el trabajo e impide que se note la saturación en varios núcleos.

Uso: python scripts/simular_saturacion_recursos.py
"""

import json
import multiprocessing
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psutil  # noqa: E402

from hsf_app.os_resources import obtener_snapshot_recursos  # noqa: E402

DURACION_SEGUNDOS = 4
PROCESOS = psutil.cpu_count(logical=True) or 4


def trabajo_intensivo(fin: float) -> None:
    total = 0
    while time.time() < fin:
        total += sum(i * i for i in range(2000))


def main() -> None:
    print("--- snapshot ANTES ---")
    antes = obtener_snapshot_recursos()
    print(json.dumps({k: antes[k] for k in ("cpu_percent", "memoria_percent", "disco_percent")}, indent=2))

    fin = time.time() + DURACION_SEGUNDOS
    procesos = [multiprocessing.Process(target=trabajo_intensivo, args=(fin,)) for _ in range(PROCESOS)]
    for proceso in procesos:
        proceso.start()

    cpu_durante = psutil.cpu_percent(interval=DURACION_SEGUNDOS)

    for proceso in procesos:
        proceso.join()

    print(f"--- cpu_percent DURANTE la saturación ({PROCESOS} procesos) ---")
    print(cpu_durante)

    print("--- snapshot DESPUÉS ---")
    despues = obtener_snapshot_recursos()
    print(json.dumps({k: despues[k] for k in ("cpu_percent", "memoria_percent", "disco_percent")}, indent=2))

    evidencia = {
        "procesos_lanzados": PROCESOS,
        "duracion_segundos": DURACION_SEGUNDOS,
        "antes": {k: antes[k] for k in ("cpu_percent", "memoria_percent", "disco_percent")},
        "cpu_percent_durante_saturacion": cpu_durante,
        "despues": {k: despues[k] for k in ("cpu_percent", "memoria_percent", "disco_percent")},
    }
    ruta_salida = Path(__file__).resolve().parent.parent / "data" / "fallo5_saturacion_cpu.json"
    ruta_salida.write_text(json.dumps(evidencia, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"evidencia guardada en {ruta_salida}")


if __name__ == "__main__":
    main()
