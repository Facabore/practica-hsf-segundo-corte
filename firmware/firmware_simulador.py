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

Como un microcontrolador real con consola serie de mantenimiento, acepta
comandos por la entrada estándar (escribirlos en su terminal y Enter, o
enviados por el lanzador de la demo). Solo existe una lista cerrada de
comandos; cualquier otra cosa se ignora, nunca se ejecuta.
"""

import argparse
import json
import queue
import random
import socket
import sys
import threading
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


def escribir_manifiesto(puerto: int) -> None:
    manifiesto = {
        "device_id": DEVICE_ID,
        "tipo": "simulador-software",
        "variables": ["temperatura_c", "humedad_pct", "vibracion_mm_s"],
        "protocolo": "tcp-json-lines",
        "host": HOST,
        "puerto": puerto,
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


COMANDOS_FIRMWARE = ("dato_corrupto", "fuera_de_rango", "forzar_anomalia")


def interpretar_comando(linea: str) -> str | None:
    comando = linea.strip().lower()
    return comando if comando in COMANDOS_FIRMWARE else None


def generar_trama(contador: int, comando: str | None) -> bytes:
    if comando == "dato_corrupto":
        return b"TRAMA-CORRUPTA-INYECTADA\n"
    lectura = generar_lectura(contador)
    if comando == "fuera_de_rango":
        lectura["humedad_pct"] = 250.0
    elif comando == "forzar_anomalia":
        lectura["vibracion_mm_s"] = round(random.uniform(8.0, 15.0), 2)
    return (json.dumps(lectura, ensure_ascii=False) + "\n").encode("utf-8")


def escuchar_comandos(cola: queue.Queue, entrada=None) -> None:
    for linea in entrada if entrada is not None else sys.stdin:
        comando = interpretar_comando(linea)
        if comando:
            cola.put(comando)
            print(f"[firmware] comando recibido: {comando}", flush=True)
        elif linea.strip():
            print(f"[firmware] comando desconocido, ignorado: {linea.strip()!r}", flush=True)


def crear_servidor(host: str, puerto: int) -> socket.socket:
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # En Linux, SO_REUSEADDR solo evita esperar el TIME_WAIT tras un reinicio.
    # En Windows permitiría que dos procesos escuchen el mismo puerto a la
    # vez, así que ahí se deja el comportamiento por defecto (exclusivo).
    if sys.platform != "win32":
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        servidor.bind((host, puerto))
        servidor.listen(1)
    except OSError:
        servidor.close()
        raise
    return servidor


def atender_cliente(conexion: socket.socket, comandos: queue.Queue) -> None:
    contador = 0
    with conexion:
        while True:
            try:
                comando = comandos.get_nowait()
            except queue.Empty:
                comando = None
            try:
                conexion.sendall(generar_trama(contador, comando))
            except OSError:
                print("[firmware] cliente desconectado", flush=True)
                return
            contador += 1
            time.sleep(INTERVALO_SEGUNDOS)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=f"Firmware simulado del dispositivo {DEVICE_ID}")
    parser.add_argument("--puerto", type=int, default=PUERTO, help=f"puerto TCP (por defecto {PUERTO})")
    puerto = parser.parse_args(argv).puerto

    escribir_manifiesto(puerto)
    comandos = queue.Queue()
    threading.Thread(target=escuchar_comandos, args=(comandos,), daemon=True).start()
    try:
        servidor = crear_servidor(HOST, puerto)
    except OSError as exc:
        print(f"[firmware] no se pudo abrir {HOST}:{puerto} (¿otro firmware ya está corriendo?): {exc}", flush=True)
        sys.exit(1)
    with servidor:
        print(f"[firmware] escuchando en {HOST}:{puerto} como {DEVICE_ID}", flush=True)
        print(f"[firmware] comandos de mantenimiento: {', '.join(COMANDOS_FIRMWARE)}", flush=True)
        try:
            while True:
                conexion, direccion = servidor.accept()
                print(f"[firmware] cliente conectado desde {direccion}", flush=True)
                atender_cliente(conexion, comandos)
        except KeyboardInterrupt:
            print("[firmware] detenido por el usuario", flush=True)
            sys.exit(0)


if __name__ == "__main__":
    main()
