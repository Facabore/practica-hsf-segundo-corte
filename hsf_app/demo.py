"""Demo en vivo: firmware + aplicación + dashboard con un solo comando.

Uso:  python -m hsf_app.demo          (en Windows también: doble clic en DEMO.bat)

Levanta el firmware simulado como un proceso aparte (igual que un
dispositivo real separado del computador), corre el orquestador en un
hilo, sirve el dashboard en http://127.0.0.1:8080 y abre el navegador.
Los botones de "fallos controlados" del dashboard llegan a ControladorDemo.
"""

import argparse
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
    DEMO_CSV_PATH,
    DEMO_LOG_PATH,
    DEMO_REPORTE_PATH,
    FIRMWARE_HOST,
    FIRMWARE_PORT,
)
from hsf_app.dashboard import crear_servidor_dashboard
from hsf_app.estado import EstadoIntegracion, ManejadorEventos
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
    comandos = {
        "detener_firmware": ("Detener el firmware", "Mata el proceso: la app detecta la caída y reintenta"),
        "iniciar_firmware": ("Reiniciar el firmware", "Lo vuelve a levantar: la app se reconecta sola"),
        "dato_corrupto": ("Enviar dato corrupto", "La próxima trama no es JSON: se descarta y se sigue"),
        "fuera_de_rango": ("Valor fuera de rango", "Humedad de 250 %: la validación la rechaza"),
        "forzar_anomalia": ("Forzar una anomalía", "Vibración alta pero válida: se marca como anómala"),
        "saturar_cpu": ("Saturar la CPU 5 s", "Procesos de cálculo intensivo: mirá la gráfica de CPU"),
    }

    def __init__(self, logger, puerto_firmware: int = FIRMWARE_PORT):
        self.logger = logger
        self.puerto_firmware = puerto_firmware
        self._firmware: subprocess.Popen | None = None
        self._saturadores: list[subprocess.Popen] = []
        self._lock = threading.Lock()
        self._acciones = {
            "detener_firmware": self.detener_firmware,
            "iniciar_firmware": self.iniciar_firmware,
            "dato_corrupto": lambda: self._enviar_al_firmware("dato_corrupto"),
            "fuera_de_rango": lambda: self._enviar_al_firmware("fuera_de_rango"),
            "forzar_anomalia": lambda: self._enviar_al_firmware("forzar_anomalia"),
            "saturar_cpu": self.saturar_cpu,
        }

    def ejecutar(self, nombre: str) -> str:
        accion = self._acciones.get(nombre)
        return accion() if accion else f"comando desconocido: {nombre}"

    def firmware_activo(self) -> bool:
        return self._firmware is not None and self._firmware.poll() is None

    def iniciar_firmware(self) -> str:
        with self._lock:
            if self.firmware_activo():
                return "El firmware ya está corriendo"
            self._firmware = subprocess.Popen(
                [sys.executable, "-u", str(FIRMWARE_SCRIPT), "--puerto", str(self.puerto_firmware)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=BASE_DIR,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            proceso = self._firmware
        threading.Thread(target=self._reenviar_salida, args=(proceso,), daemon=True).start()
        self.logger.info("firmware iniciado (PID %s, puerto %s)", proceso.pid, self.puerto_firmware)
        return f"Firmware iniciado (PID {proceso.pid})"

    def _reenviar_salida(self, proceso: subprocess.Popen) -> None:
        for linea in proceso.stdout:
            if linea.strip():
                self.logger.info("%s", linea.strip())

    def detener_firmware(self) -> str:
        with self._lock:
            if not self.firmware_activo():
                return "El firmware ya estaba detenido"
            proceso = self._firmware
            proceso.terminate()
            try:
                proceso.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait(timeout=3)
        self.logger.warning("firmware detenido a propósito desde la demo (PID %s)", proceso.pid)
        return "Firmware detenido: la app detecta la caída y empieza a reintentar"

    def _enviar_al_firmware(self, comando: str) -> str:
        with self._lock:
            if not self.firmware_activo():
                return "El firmware está detenido: reinicialo primero"
            self._firmware.stdin.write(comando + "\n")
            self._firmware.stdin.flush()
        return f"Comando «{comando}» enviado: llega en la próxima trama"

    def saturar_cpu(self) -> str:
        self._saturadores = [p for p in self._saturadores if p.poll() is None]
        if self._saturadores:
            return "La CPU ya se está saturando; esperá a que termine"
        nucleos = os.cpu_count() or 4
        self._saturadores = [subprocess.Popen([sys.executable, "-c", CODIGO_SATURACION]) for _ in range(nucleos)]
        self.logger.warning("saturando la CPU con %s procesos durante %s s", nucleos, SEGUNDOS_SATURACION)
        return f"Saturando {nucleos} núcleos durante {SEGUNDOS_SATURACION} s"

    def cerrar(self) -> None:
        if self.firmware_activo():
            self.detener_firmware()
        for proceso in self._saturadores:
            if proceso.poll() is None:
                proceso.kill()


def main(argv=None) -> int:  # pragma: no cover - punto de entrada interactivo
    parser = argparse.ArgumentParser(description="Demo en vivo de la práctica HSF: firmware + app + dashboard")
    parser.add_argument("--puerto", type=int, default=DASHBOARD_PORT, help=f"puerto del dashboard (por defecto {DASHBOARD_PORT})")
    parser.add_argument("--sin-navegador", action="store_true", help="no abrir el navegador automáticamente")
    args = parser.parse_args(argv)

    if puerto_en_uso(FIRMWARE_HOST, FIRMWARE_PORT):
        print(f"Ya hay algo escuchando en {FIRMWARE_HOST}:{FIRMWARE_PORT} (¿quedó abierto otro firmware?). Cerralo y volvé a intentar.")
        return 1

    estado = EstadoIntegracion()
    logger = configurar_logging("hsf-demo", DEMO_LOG_PATH)
    logger.addHandler(ManejadorEventos(estado))
    controlador = ControladorDemo(logger)
    muestreador = MuestreadorCPU()

    try:
        servidor = crear_servidor_dashboard(estado, controlador, puerto=args.puerto, muestreador_cpu=muestreador)
    except OSError as exc:
        print(f"No se pudo abrir el dashboard en el puerto {args.puerto} ({exc}). Probá con: python -m hsf_app.demo --puerto 8081")
        return 1
    muestreador.iniciar()

    controlador.iniciar_firmware()
    orquestador = OrquestadorHSF(
        fuente=FuenteAdquisicion(backoff_seconds=BACKOFF_DEMO),
        logger=logger,
        ruta_csv=DEMO_CSV_PATH,
        ruta_reporte=DEMO_REPORTE_PATH,
        estado=estado,
        reintentar_siempre=True,
    )
    hilo = threading.Thread(target=orquestador.ejecutar, name="orquestador", daemon=True)
    hilo.start()
    threading.Thread(target=servidor.serve_forever, name="dashboard", daemon=True).start()

    url = f"http://127.0.0.1:{args.puerto}/"
    print("=" * 66)
    print(" Demo HSF en vivo")
    print(f" Dashboard:  {url}")
    print(f" Firmware:   {FIRMWARE_HOST}:{FIRMWARE_PORT}")
    print(f" Datos de esta demo: {DEMO_CSV_PATH.name}, {DEMO_REPORTE_PATH.name}, {DEMO_LOG_PATH.name}")
    print(" Para terminar: Ctrl+C en esta ventana")
    print("=" * 66, flush=True)
    if not args.sin_navegador:
        webbrowser.open(url)

    try:
        while hilo.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nCerrando la demo…")
    finally:
        orquestador.detener()
        hilo.join(timeout=5)
        servidor.shutdown()
        servidor.server_close()
        muestreador.detener()
        controlador.cerrar()
        print(f"Reporte final de esta demo: {DEMO_REPORTE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
