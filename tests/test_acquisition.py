import socket
import threading
import time

import pytest

from hsf_app.acquisition import ErrorAdquisicion, FuenteAdquisicion


def _servidor_que_envia(lineas, puertos, cerrar_despues=False):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(1)
    puertos.append(servidor.getsockname()[1])

    def _run():
        conexion, _ = servidor.accept()
        with conexion:
            for linea in lineas:
                conexion.sendall(linea.encode("utf-8"))
            if cerrar_despues:
                return
            time.sleep(0.3)

    hilo = threading.Thread(target=_run, daemon=True)
    hilo.start()
    return servidor, hilo


def test_lee_una_lectura_valida():
    puertos = []
    servidor, _ = _servidor_que_envia(
        ['{"device_id": "SIM-001", "temperatura_c": 22.0}\n'], puertos
    )
    with servidor:
        time.sleep(0.05)
        fuente = FuenteAdquisicion(host="127.0.0.1", port=puertos[0])
        fuente.conectar()
        lectura = fuente.leer_siguiente()
        fuente.cerrar()

    assert lectura["device_id"] == "SIM-001"
    assert lectura["temperatura_c"] == 22.0


def test_linea_corrupta_lanza_error_adquisicion_y_sigue():
    puertos = []
    servidor, _ = _servidor_que_envia(
        ["no-es-json\n", '{"device_id": "SIM-001"}\n'], puertos
    )
    with servidor:
        time.sleep(0.05)
        fuente = FuenteAdquisicion(host="127.0.0.1", port=puertos[0])
        fuente.conectar()

        with pytest.raises(ErrorAdquisicion):
            fuente.leer_siguiente()

        lectura = fuente.leer_siguiente()
        fuente.cerrar()

    assert lectura["device_id"] == "SIM-001"


def test_conexion_cerrada_por_el_servidor_lanza_connection_error():
    puertos = []
    servidor, _ = _servidor_que_envia([], puertos, cerrar_despues=True)
    with servidor:
        time.sleep(0.05)
        fuente = FuenteAdquisicion(host="127.0.0.1", port=puertos[0])
        fuente.conectar()
        with pytest.raises(ConnectionError):
            fuente.leer_siguiente()
        fuente.cerrar()


def test_firmware_colgado_sin_datos_se_trata_como_conexion_perdida():
    puertos = []
    servidor, _ = _servidor_que_envia([], puertos)  # acepta y no envía nada
    with servidor:
        time.sleep(0.05)
        fuente = FuenteAdquisicion(host="127.0.0.1", port=puertos[0], timeout=0.1)
        fuente.conectar()
        with pytest.raises(ConnectionError, match="sin datos"):
            fuente.leer_siguiente()
        fuente.cerrar()


def test_conectar_con_reintentos_reintenta_hasta_exito(monkeypatch):
    fuente = FuenteAdquisicion(host="127.0.0.1", port=9, backoff_seconds=(0, 0))
    intentos = {"n": 0}

    def conectar_falso():
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise OSError("rechazada")

    monkeypatch.setattr(fuente, "conectar", conectar_falso)
    exito = fuente.conectar_con_reintentos()

    assert exito is True
    assert intentos["n"] == 3


def test_conectar_con_reintentos_se_cancela_sin_esperar_el_backoff(monkeypatch):
    fuente = FuenteAdquisicion(host="127.0.0.1", port=9, backoff_seconds=(5, 5))

    def siempre_falla():
        raise OSError("nunca conecta")

    monkeypatch.setattr(fuente, "conectar", siempre_falla)
    cancelado = threading.Event()
    cancelado.set()

    inicio = time.time()
    exito = fuente.conectar_con_reintentos(cancelado=cancelado)

    assert exito is False
    assert time.time() - inicio < 1


def test_leer_despues_de_cerrar_lanza_connection_error():
    fuente = FuenteAdquisicion(host="127.0.0.1", port=9)
    fuente.cerrar()

    with pytest.raises(ConnectionError):
        fuente.leer_siguiente()


def test_conectar_con_reintentos_agota_intentos_y_devuelve_false(monkeypatch):
    fuente = FuenteAdquisicion(host="127.0.0.1", port=9, backoff_seconds=(0, 0))

    def siempre_falla():
        raise OSError("nunca conecta")

    monkeypatch.setattr(fuente, "conectar", siempre_falla)
    exito = fuente.conectar_con_reintentos()

    assert exito is False
