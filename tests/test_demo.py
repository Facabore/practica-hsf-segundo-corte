import json
import logging
import socket
import time

import pytest

from hsf_app.demo import ControladorDemo, puerto_en_uso


def _puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _logger():
    logger = logging.getLogger("test-demo")
    logger.addHandler(logging.NullHandler())
    return logger


def _conectar(puerto, intentos=40):
    for _ in range(intentos):
        try:
            return socket.create_connection(("127.0.0.1", puerto), timeout=3)
        except OSError:
            time.sleep(0.1)
    raise AssertionError("el firmware nunca aceptó conexiones")


def _lineas(conexion, cantidad):
    buffer = b""
    while buffer.count(b"\n") < cantidad:
        buffer += conexion.recv(4096)
    return buffer.split(b"\n")[:cantidad]


@pytest.fixture
def controlador():
    c = ControladorDemo(_logger(), puerto_firmware=_puerto_libre())
    yield c
    c.cerrar()


def test_comando_con_el_firmware_detenido_avisa_sin_fallar(controlador):
    assert "detenido" in controlador.ejecutar("dato_corrupto")


def test_iniciar_y_detener_el_firmware_real(controlador):
    controlador.ejecutar("iniciar_firmware")
    with _conectar(controlador.puerto_firmware) as conexion:
        lectura = json.loads(_lineas(conexion, 1)[0])
    assert lectura["device_id"] == "SIM-001"

    controlador.ejecutar("detener_firmware")
    assert not controlador.firmware_activo()


def test_iniciar_dos_veces_no_duplica_el_firmware(controlador):
    controlador.ejecutar("iniciar_firmware")

    assert "ya está corriendo" in controlador.ejecutar("iniciar_firmware")


def test_el_comando_llega_al_firmware_real(controlador):
    controlador.ejecutar("iniciar_firmware")
    with _conectar(controlador.puerto_firmware) as conexion:
        _lineas(conexion, 1)
        controlador.ejecutar("dato_corrupto")
        lineas = _lineas(conexion, 4)
    assert b"TRAMA-CORRUPTA-INYECTADA" in lineas


def test_puerto_en_uso_detecta_un_servidor_escuchando():
    with socket.socket() as servidor:
        servidor.bind(("127.0.0.1", 0))
        servidor.listen(1)
        puerto = servidor.getsockname()[1]
        assert puerto_en_uso("127.0.0.1", puerto)
    assert not puerto_en_uso("127.0.0.1", puerto)
