import http.client
import json
import threading

import pytest

from hsf_app.dashboard import crear_servidor_dashboard
from hsf_app.estado import EstadoIntegracion


class ControladorFalso:
    comandos = {"forzar_anomalia": ("Forzar anomalía", "La próxima trama llega anómala")}

    def __init__(self):
        self.ejecutados = []

    def ejecutar(self, nombre):
        self.ejecutados.append(nombre)
        return f"ejecutado {nombre}"


class MuestreadorFalso:
    ultimo = 37.5


@pytest.fixture
def dashboard():
    controlador = ControladorFalso()
    servidor = crear_servidor_dashboard(EstadoIntegracion(), controlador, puerto=0, muestreador_cpu=MuestreadorFalso())
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield servidor, controlador
    servidor.shutdown()
    servidor.server_close()


def _pedir(servidor, ruta, metodo="GET", cabeceras=None):
    conexion = http.client.HTTPConnection("127.0.0.1", servidor.server_address[1], timeout=3)
    try:
        conexion.request(metodo, ruta, body=b"" if metodo == "POST" else None, headers=cabeceras or {})
        respuesta = conexion.getresponse()
        return respuesta.status, respuesta.read()
    finally:
        conexion.close()


def test_sirve_la_pagina_del_dashboard(dashboard):
    servidor, _ = dashboard

    status, cuerpo = _pedir(servidor, "/")

    assert status == 200
    assert b"<html" in cuerpo.lower()


def test_api_estado_devuelve_estado_recursos_y_comandos(dashboard):
    servidor, _ = dashboard

    status, cuerpo = _pedir(servidor, "/api/estado")

    datos = json.loads(cuerpo)
    assert status == 200
    assert datos["conexion"] == "iniciando"
    assert datos["recursos"]["cpu_percent"] == 37.5
    assert datos["comandos"][0]["nombre"] == "forzar_anomalia"
    assert datos["rangos_normales"]["temperatura_c"] == [10.0, 45.0]


def test_comando_sin_cabecera_de_la_demo_es_rechazado(dashboard):
    servidor, controlador = dashboard

    status, _ = _pedir(servidor, "/api/comando/forzar_anomalia", metodo="POST")

    assert status == 403
    assert controlador.ejecutados == []


def test_comando_valido_con_cabecera_se_ejecuta(dashboard):
    servidor, controlador = dashboard

    status, cuerpo = _pedir(servidor, "/api/comando/forzar_anomalia", metodo="POST", cabeceras={"X-HSF-Demo": "1"})

    assert status == 200
    assert json.loads(cuerpo)["mensaje"] == "ejecutado forzar_anomalia"
    assert controlador.ejecutados == ["forzar_anomalia"]


def test_comando_fuera_de_la_lista_cerrada_no_existe(dashboard):
    servidor, controlador = dashboard

    status, _ = _pedir(servidor, "/api/comando/borrar_todo", metodo="POST", cabeceras={"X-HSF-Demo": "1"})

    assert status == 404
    assert controlador.ejecutados == []


def test_host_ajeno_es_rechazado_contra_dns_rebinding(dashboard):
    servidor, _ = dashboard

    status, _ = _pedir(servidor, "/api/estado", cabeceras={"Host": "sitio-malicioso.example"})

    assert status == 403


def test_ruta_desconocida_da_404(dashboard):
    servidor, _ = dashboard

    status, _ = _pedir(servidor, "/no-existe")

    assert status == 404
