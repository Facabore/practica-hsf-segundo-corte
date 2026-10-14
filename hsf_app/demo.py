"""Demo en vivo: varios dispositivos + aplicación + dashboard con un solo comando.

Uso:  python -m hsf_app.demo          (en Windows también: doble clic en DEMO.bat)

Levanta un firmware simulado por cada equipo de DISPOSITIVOS_DEMO, cada uno
como un proceso aparte con su propio puerto (igual que aparatos separados
del computador). Corre un orquestador por equipo, cada uno en su hilo con su
propia conexión, estado y CSV, sirve el dashboard en http://127.0.0.1:8080
y abre el navegador. Los botones del dashboard llegan a ControladorDemo.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

from hsf_app.acquisition import FuenteAdquisicion
from hsf_app.app import OrquestadorHSF
from hsf_app.config import (
    BASE_DIR,
    DASHBOARD_PORT,
    DATA_DIR,
    DEMO_LOG_PATH,
    DEMO_REPORTE_GENERAL_PATH,
    DISPOSITIVOS_DEMO,
    FIRMWARE_HOST,
    Dispositivo,
)
from hsf_app.dashboard import crear_servidor_dashboard
from hsf_app.estado import EstadoIntegracion, ManejadorEventos
from hsf_app.flota import EstadoFlota, LoggerDispositivo
from hsf_app.logging_setup import configurar_logging
from hsf_app.os_resources import MuestreadorCPU

FIRMWARE_SCRIPT = BASE_DIR / "firmware" / "firmware_simulador.py"
SEGUNDOS_SATURACION = 5
# Código fijo de cada proceso saturador; nunca se arma con datos externos.
CODIGO_SATURACION = f"import time\nfin = time.time() + {SEGUNDOS_SATURACION}\nwhile time.time() < fin:\n    pass\n"
# Backoff más corto que el de producción para que la reconexión se vea rápido en el video.
BACKOFF_DEMO = (1, 2, 2, 2)


def puerto_en_uso(host: str, puerto: int) -> bool:
    try:
        with socket.create_connection((host, puerto), timeout=0.5):
            return True
    except OSError:
        return False


class ControladorDemo:
    comandos_dispositivo = {
        "detener_firmware": ("Detener el firmware", "Mata el proceso: la app detecta la caída y reintenta"),
        "iniciar_firmware": ("Reiniciar el firmware", "Lo vuelve a levantar: la app se reconecta sola"),
        "dato_corrupto": ("Enviar dato corrupto", "La próxima trama no es JSON: se descarta y se sigue"),
        "fuera_de_rango": ("Valor fuera de rango", "Humedad de 250 %: la validación la rechaza"),
        "forzar_anomalia": ("Forzar una anomalía", "Vibración alta pero válida: se marca como anómala"),
    }
    comandos_globales = {
        "saturar_cpu": ("Saturar la CPU 5 s", "Procesos de cálculo intensivo: mirá la gráfica de CPU"),
    }

    def __init__(self, logger, dispositivos=DISPOSITIVOS_DEMO):
        self.logger = logger
        self.dispositivos: dict[str, Dispositivo] = {d.id: d for d in dispositivos}
        self._firmwares: dict[str, subprocess.Popen] = {}
        self._saturadores: list[subprocess.Popen] = []
        self._lock = threading.Lock()

    def _log(self, dispositivo_id: str) -> LoggerDispositivo:
        return LoggerDispositivo(self.logger, {"id": dispositivo_id})

    def ejecutar(self, nombre: str, dispositivo: str | None = None) -> str:
        if dispositivo is None:
            return self.saturar_cpu() if nombre == "saturar_cpu" else f"el comando {nombre} necesita un dispositivo"
        if dispositivo not in self.dispositivos:
            return f"dispositivo desconocido: {dispositivo}"
        if nombre == "iniciar_firmware":
            return self.iniciar_firmware(dispositivo)
        if nombre == "detener_firmware":
            return self.detener_firmware(dispositivo)
        if nombre in ("dato_corrupto", "fuera_de_rango", "forzar_anomalia"):
            return self._enviar_al_firmware(dispositivo, nombre)
        return f"comando desconocido: {nombre}"

    def firmware_activo(self, dispositivo_id: str) -> bool:
        proceso = self._firmwares.get(dispositivo_id)
        return proceso is not None and proceso.poll() is None

    def iniciar_todos(self) -> None:
        for dispositivo_id in self.dispositivos:
            self.iniciar_firmware(dispositivo_id)

    def iniciar_firmware(self, dispositivo_id: str) -> str:
        d = self.dispositivos[dispositivo_id]
        with self._lock:
            if self.firmware_activo(d.id):
                return f"El firmware de {d.id} ya está corriendo"
            proceso = subprocess.Popen(
                [
                    sys.executable, "-u", str(FIRMWARE_SCRIPT),
                    "--puerto", str(d.puerto), "--device-id", d.id, "--ciclos-anomalia", str(d.ciclos_anomalia),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=BASE_DIR,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            self._firmwares[d.id] = proceso
        threading.Thread(target=self._reenviar_salida, args=(d.id, proceso), daemon=True).start()
        self._log(d.id).info("firmware iniciado (PID %s, puerto %s)", proceso.pid, d.puerto)
        return f"Firmware de {d.id} iniciado (PID {proceso.pid})"

    def _reenviar_salida(self, dispositivo_id: str, proceso: subprocess.Popen) -> None:
        log = self._log(dispositivo_id)
        for linea in proceso.stdout:
            if linea.strip():
                log.info("%s", linea.strip())

    def detener_firmware(self, dispositivo_id: str) -> str:
        with self._lock:
            if not self.firmware_activo(dispositivo_id):
                return f"El firmware de {dispositivo_id} ya estaba detenido"
            proceso = self._firmwares[dispositivo_id]
            proceso.terminate()
            try:
                proceso.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait(timeout=3)
        self._log(dispositivo_id).warning("firmware detenido a propósito desde la demo (PID %s)", proceso.pid)
        return f"Firmware de {dispositivo_id} detenido: la app detecta la caída y reintenta; los demás siguen"

    def _enviar_al_firmware(self, dispositivo_id: str, comando: str) -> str:
        with self._lock:
            if not self.firmware_activo(dispositivo_id):
                return f"El firmware de {dispositivo_id} está detenido: reinicialo primero"
            proceso = self._firmwares[dispositivo_id]
            proceso.stdin.write(comando + "\n")
            proceso.stdin.flush()
        return f"Comando «{comando}» enviado a {dispositivo_id}: llega en su próxima trama"

    def saturar_cpu(self) -> str:
        self._saturadores = [p for p in self._saturadores if p.poll() is None]
        if self._saturadores:
            return "La CPU ya se está saturando; esperá a que termine"
        nucleos = os.cpu_count() or 4
        self._saturadores = [subprocess.Popen([sys.executable, "-c", CODIGO_SATURACION]) for _ in range(nucleos)]
        self.logger.warning("saturando la CPU con %s procesos durante %s s", nucleos, SEGUNDOS_SATURACION)
        return f"Saturando {nucleos} núcleos durante {SEGUNDOS_SATURACION} s"

    def cerrar(self) -> None:
        for dispositivo_id in self.dispositivos:
            if self.firmware_activo(dispositivo_id):
                self.detener_firmware(dispositivo_id)
        for proceso in self._saturadores:
            if proceso.poll() is None:
                proceso.kill()


def main(argv=None) -> int:  # pragma: no cover - punto de entrada interactivo
    parser = argparse.ArgumentParser(description="Demo en vivo de la práctica HSF: varios dispositivos + app + dashboard")
    parser.add_argument("--puerto", type=int, default=DASHBOARD_PORT, help=f"puerto del dashboard (por defecto {DASHBOARD_PORT})")
    parser.add_argument("--sin-navegador", action="store_true", help="no abrir el navegador automáticamente")
    parser.add_argument("--host-publico", action="append", default=[], metavar="DOMINIO",
                        help="dominio con el que llega el tráfico desde un proxy como Caddy (repetible)")
    parser.add_argument("--solo-lectura", action="store_true",
                        help="desactiva los botones de fallos (para publicar en internet)")
    args = parser.parse_args(argv)

    ocupados = [d for d in DISPOSITIVOS_DEMO if puerto_en_uso(FIRMWARE_HOST, d.puerto)]
    if ocupados:
        puertos = ", ".join(str(d.puerto) for d in ocupados)
        print(f"Ya hay algo escuchando en {FIRMWARE_HOST}:{puertos} (¿quedó abierto otro firmware?). Cerralo y volvé a intentar.")
        return 1

    logger = configurar_logging("hsf-demo", DEMO_LOG_PATH)
    estados = {d.id: EstadoIntegracion() for d in DISPOSITIVOS_DEMO}
    flota = EstadoFlota([(d, estados[d.id]) for d in DISPOSITIVOS_DEMO])
    logger.addHandler(ManejadorEventos(flota))
    controlador = ControladorDemo(logger)
    muestreador = MuestreadorCPU()

    try:
        servidor = crear_servidor_dashboard(
            flota, controlador, puerto=args.puerto, muestreador_cpu=muestreador,
            hosts_publicos=args.host_publico, solo_lectura=args.solo_lectura,
        )
    except OSError as exc:
        print(f"No se pudo abrir el dashboard en el puerto {args.puerto} ({exc}). Probá con: python -m hsf_app.demo --puerto 8081")
        return 1
    muestreador.iniciar()
    controlador.iniciar_todos()

    orquestadores, hilos = [], []
    for d in DISPOSITIVOS_DEMO:
        orquestador = OrquestadorHSF(
            fuente=FuenteAdquisicion(port=d.puerto, backoff_seconds=BACKOFF_DEMO),
            logger=LoggerDispositivo(logger, {"id": d.id}),
            ruta_csv=DATA_DIR / f"demo_lecturas_{d.id}.csv",
            ruta_reporte=DATA_DIR / f"demo_reporte_{d.id}.json",
            estado=estados[d.id],
            reintentar_siempre=True,
        )
        hilo = threading.Thread(target=orquestador.ejecutar, name=f"orquestador-{d.id}", daemon=True)
        hilo.start()
        orquestadores.append(orquestador)
        hilos.append(hilo)
    threading.Thread(target=servidor.serve_forever, name="dashboard", daemon=True).start()

    url = f"http://127.0.0.1:{args.puerto}/"
    print("=" * 66)
    print(" Demo HSF en vivo")
    print(f" Dashboard:  {url}")
    for d in DISPOSITIVOS_DEMO:
        print(f" {d.id} · {d.nombre}: {FIRMWARE_HOST}:{d.puerto}")
    print(" Datos de esta demo: data/demo_*, logs/demo.log")
    print(" Para terminar: Ctrl+C en esta ventana")
    print("=" * 66, flush=True)
    if not args.sin_navegador:
        webbrowser.open(url)

    try:
        while any(h.is_alive() for h in hilos):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nCerrando la demo…")
    finally:
        for orquestador in orquestadores:
            orquestador.detener()
        for hilo in hilos:
            hilo.join(timeout=5)
        servidor.shutdown()
        servidor.server_close()
        muestreador.detener()
        controlador.cerrar()
        DEMO_REPORTE_GENERAL_PATH.write_text(
            json.dumps(flota.snapshot()["general"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Reportes de esta demo: data/demo_reporte_<equipo>.json y {DEMO_REPORTE_GENERAL_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
