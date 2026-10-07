"""Firmware simulado del dispositivo (capa Hardware+Firmware).

Actúa como un microcontrolador emulado: abre un servidor TCP y, por cada
cliente que se conecta (la aplicación Python), emite una trama JSON por
línea cada `INTERVALO_SEGUNDOS`. Cada trama identifica el dispositivo
(RF01) y trae tres variables físicas. Cada `CICLOS_POR_ANOMALIA` lecturas,
inyecta deliberadamente una condición anómala para que la capa de
procesamiento la detecte (RF04).

No depende de hardware real ni de librerías externas: solo usa `socket`,
`json` y `random` de la librería estándar, así corre igual en Windows y
en Linux (requisito de portabilidad).
"""

import json
import random
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOST = "127.0.0.1"
PUERTO = 8765
DEVICE_ID = "SIM-001"
INTERVALO_SEGUNDOS = 1.0
CICLOS_POR_ANOMALIA = 7

BASE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = BASE_DIR / "device_manifest.json"


def escribir_manifiesto() -> None:
    manifiesto = {
        "device_id": DEVICE_ID,
        "tipo": "simulador-software",
        "variables": ["temperatura_c", "humedad_pct", "vibracion_mm_s"],
        "protocolo": "tcp-json-lines",
        "host": HOST,
        "puerto": PUERTO,
        "generado_en": datetime.now(timezone.utc).isoformat(),
    }
    MANIFEST_PATH.write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False), encoding="utf-8")


def generar_lectura(contador: int) -> dict:
    anomalo = contador > 0 and contador % CICLOS_POR_ANOMALIA == 0

    if anomalo:
        variable_afectada = random.choice(["temperatura_c", "humedad_pct", "vibracion_mm_s"])
        valores = {
            "temperatura_c": round(random.uniform(15.0, 30.0), 2),
            "humedad_pct": round(random.uniform(35.0, 60.0), 2),
            "vibracion_mm_s": round(random.uniform(0.5, 2.5), 2),
        }
        if variable_afectada == "temperatura_c":
            valores["temperatura_c"] = round(random.uniform(55.0, 80.0), 2)
        elif variable_afectada == "humedad_pct":
            valores["humedad_pct"] = round(random.uniform(0.0, 5.0), 2)
        else:
            valores["vibracion_mm_s"] = round(random.uniform(8.0, 15.0), 2)
    else:
        valores = {
            "temperatura_c": round(random.uniform(18.0, 28.0), 2),
            "humedad_pct": round(random.uniform(35.0, 60.0), 2),
            "vibracion_mm_s": round(random.uniform(0.3, 2.0), 2),
        }

    return {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **valores,
    }


def atender_cliente(conexion: socket.socket) -> None:
    contador = 0
    with conexion:
        while True:
            lectura = generar_lectura(contador)
            linea = (json.dumps(lectura, ensure_ascii=False) + "\n").encode("utf-8")
            try:
                conexion.sendall(linea)
            except (BrokenPipeError, ConnectionResetError, OSError):
                print("[firmware] cliente desconectado")
                return
            contador += 1
            time.sleep(INTERVALO_SEGUNDOS)


def main() -> None:
    escribir_manifiesto()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, PUERTO))
        servidor.listen(1)
        print(f"[firmware] escuchando en {HOST}:{PUERTO} como {DEVICE_ID}")
        try:
            while True:
                conexion, direccion = servidor.accept()
                print(f"[firmware] cliente conectado desde {direccion}")
                atender_cliente(conexion)
        except KeyboardInterrupt:
            print("[firmware] detenido por el usuario")
            sys.exit(0)


if __name__ == "__main__":
    main()
