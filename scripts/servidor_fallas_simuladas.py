"""Servidor TCP deliberadamente defectuoso, solo para reproducir fallos
controlados (Anexo 3 §11) de forma determinística — no es el firmware
normal (ver `firmware/firmware_simulador.py`).

Por cada cliente que conecta, envía en orden:
  1. una línea con JSON corrupto (fallo "dato con formato incorrecto"),
  2. una lectura válida y normal,
  3. una lectura con una variable fuera del rango físicamente válido
     (fallo "variable fuera del rango esperado"),
  4. una lectura válida y normal,
y después mantiene la conexión abierta un instante antes de cerrarla.

Uso: python scripts/servidor_fallas_simuladas.py [puerto]
"""

import json
import socket
import sys
import time
from datetime import datetime, timezone

HOST = "127.0.0.1"


def _lectura(**overrides):
    base = {
        "device_id": "SIM-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperatura_c": 23.0,
        "humedad_pct": 45.0,
        "vibracion_mm_s": 1.0,
    }
    base.update(overrides)
    return base


def atender_cliente(conexion: socket.socket) -> None:
    with conexion:
        conexion.sendall(b"ESTO-NO-ES-JSON-VALIDO\n")
        time.sleep(0.2)
        conexion.sendall((json.dumps(_lectura()) + "\n").encode("utf-8"))
        time.sleep(0.2)
        conexion.sendall((json.dumps(_lectura(humedad_pct=250.0)) + "\n").encode("utf-8"))
        time.sleep(0.2)
        conexion.sendall((json.dumps(_lectura()) + "\n").encode("utf-8"))
        time.sleep(1.0)


def main() -> None:
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, puerto))
        servidor.listen(1)
        print(f"[servidor-fallas] escuchando en {HOST}:{puerto}")
        while True:
            conexion, direccion = servidor.accept()
            print(f"[servidor-fallas] cliente conectado desde {direccion}")
            atender_cliente(conexion)


if __name__ == "__main__":
    main()
