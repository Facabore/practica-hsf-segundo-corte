"""Ejecuta la integración por un número acotado de lecturas y termina solo.

Útil para generar evidencia reproducible (logs, CSV, reporte) sin depender
de una interrupción manual, y para grabar el video sin tiempos de espera
abiertos. Requiere que `firmware/firmware_simulador.py` ya esté corriendo.

Uso: python scripts/ejecutar_demo_acotado.py [numero_de_lecturas]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hsf_app.acquisition import FuenteAdquisicion  # noqa: E402
from hsf_app.app import OrquestadorHSF  # noqa: E402
from hsf_app.logging_setup import configurar_logging  # noqa: E402


def main() -> None:
    numero_lecturas = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    logger = configurar_logging()
    fuente = FuenteAdquisicion()
    orquestador = OrquestadorHSF(fuente=fuente, logger=logger, max_lecturas=numero_lecturas)
    metricas = orquestador.ejecutar()
    print(f"[ESTADO] integración finalizada tras {numero_lecturas} lecturas — {metricas.resumen()}")


if __name__ == "__main__":
    main()
