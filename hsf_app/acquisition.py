"""Adquisición de datos desde el firmware simulado vía socket TCP (RF02, RF09).

`FuenteAdquisicion` encapsula la conexión al firmware y la lectura de
tramas JSON por línea. Separa dos tipos de falla para que la capa de
aplicación pueda reaccionar distinto a cada una:

- `ErrorAdquisicion`: la línea llegó pero no se pudo parsear (dato
  corrupto) — se puede descartar y seguir leyendo la conexión.
- `ConnectionError`: se perdió la conexión con el firmware — hay que
  reconectar con `conectar_con_reintentos`, no solo reintentar la lectura.
"""

import json
import socket
import threading
import time

from hsf_app.config import FIRMWARE_HOST, FIRMWARE_PORT, RECONNECT_BACKOFF_SECONDS, SOCKET_TIMEOUT_SECONDS


class ErrorAdquisicion(Exception):
    """La trama llegó pero no se pudo interpretar como una lectura válida."""


class FuenteAdquisicion:
    def __init__(
        self,
        host: str = FIRMWARE_HOST,
        port: int = FIRMWARE_PORT,
        backoff_seconds: tuple = RECONNECT_BACKOFF_SECONDS,
        timeout: float = SOCKET_TIMEOUT_SECONDS,
    ):
        self.host = host
        self.port = port
        self.backoff_seconds = backoff_seconds
        self.timeout = timeout
        self._socket: socket.socket | None = None
        self._buffer = b""

    def conectar(self) -> None:
        self._socket = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._buffer = b""

    def cerrar(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def _leer_linea_cruda(self) -> bytes:
        while b"\n" not in self._buffer:
            if self._socket is None:
                raise ConnectionError("la conexión con el firmware está cerrada")
            try:
                trozo = self._socket.recv(4096)
            except TimeoutError as exc:
                # Firmware colgado: la conexión sigue abierta pero no llegan datos.
                raise ConnectionError(f"sin datos del firmware en {self.timeout} s") from exc
            if not trozo:
                raise ConnectionError("el firmware cerró la conexión")
            self._buffer += trozo
        linea, _, self._buffer = self._buffer.partition(b"\n")
        return linea

    def leer_siguiente(self) -> dict:
        linea = self._leer_linea_cruda()
        try:
            return json.loads(linea.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ErrorAdquisicion(f"línea corrupta recibida del firmware: {exc}") from exc

    def conectar_con_reintentos(self, en_cada_intento=None, cancelado: threading.Event | None = None) -> bool:
        """Intenta conectar; si falla, reintenta con backoff creciente.

        `en_cada_intento(espera, excepcion)` es opcional, para que quien
        llame pueda loguear cada intento fallido. Si `cancelado` se activa
        durante una espera, abandona de inmediato y devuelve False.
        """
        esperas = (0, *self.backoff_seconds)
        for espera in esperas:
            if cancelado is not None and cancelado.is_set():
                return False
            if espera:
                if cancelado is not None:
                    if cancelado.wait(espera):
                        return False
                else:
                    time.sleep(espera)
            try:
                self.conectar()
                return True
            except OSError as exc:
                if en_cada_intento:
                    en_cada_intento(espera, exc)
        return False
