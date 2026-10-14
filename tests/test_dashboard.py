import http.client
import json
import threading

import pytest

from hsf_app.config import Dispositivo
from hsf_app.dashboard import crear_servidor_dashboard
from hsf_app.estado import EstadoIntegracion
from hsf_app.flota import EstadoFlota

COMPRESOR = Dispositivo("SIM-001", "Compresor", 8765, 7)


class ControladorFalso:
    comandos_globales = {"saturar_cpu": ("Saturar la CPU", "Procesos intensivos")}
    comandos_dispositivo = {"forzar_anomalia": ("Forzar anomalía", "La próxima trama llega anómala")}
    dispositivos = {COMPRESOR.id: COMPRESOR}

    def __init__(self):
        self.ejecutados = []

    def ejecutar(self, nombre, dispositivo=None):
        self.ejecutados.append((nombre, dispositivo))
        return f"ejecutado {nombre}"


class MuestreadorFalso:
    ultimo = 37.5


@pytest.fixture
def dashboard():
    controlador = ControladorFalso()
    flota = EstadoFlota([(COMPRESOR, EstadoIntegracion())])
    servidor = crear_servidor_dashboard(flota, controlador, puerto=0, muestreador_cpu=MuestreadorFalso())
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


DEMO = {"X-HSF-Demo": "1"}


def test_sirve_la_pagina_del_dashboard(dashboard):
    servidor, _ = dashboard

    status, cuerpo = _pedir(servidor, "/")

    assert status == 200
    assert b"<html" in cuerpo.lower()


def test_api_estado_trae_flota_recursos_comandos_y_rangos(dashboard):
    servidor, _ = dashboard

    status, cuerpo = _pedir(servidor, "/api/estado")

    datos = json.loads(cuerpo)
    assert status == 200
    assert datos["dispositivos"][0]["id"] == "SIM-001"
    assert datos["general"]["total"] == 1
    assert datos["recursos"]["cpu_percent"] == 37.5
    assert datos["comandos_globales"][0]["nombre"] == "saturar_cpu"
    assert datos["comandos_dispositivo"][0]["nombre"] == "forzar_anomalia"
    assert datos["rangos_normales"]["temperatura_c"] == [10.0, 45.0]


def test_comando_sin_cabecera_de_la_demo_es_rechazado(dashboard):
    servidor, controlador = dashboard

    status, _ = _pedir(servidor, "/api/comando/saturar_cpu", metodo="POST")

    assert status == 403
    assert controlador.ejecutados == []


def test_comando_global_valido_se_ejecuta_sin_dispositivo(dashboard):
    servidor, controlador = dashboard

    status, cuerpo = _pedir(servidor, "/api/comando/saturar_cpu", metodo="POST", cabeceras=DEMO)

    assert status == 200
    assert json.loads(cuerpo)["mensaje"] == "ejecutado saturar_cpu"
    assert controlador.ejecutados == [("saturar_cpu", None)]


def test_comando_de_dispositivo_llega_con_su_dispositivo(dashboard):
    servidor, controlador = dashboard

    status, _ = _pedir(servidor, "/api/dispositivo/SIM-001/comando/forzar_anomalia", metodo="POST", cabeceras=DEMO)

    assert status == 200
    assert controlador.ejecutados == [("forzar_anomalia", "SIM-001")]


@pytest.mark.parametrize("ruta", [
    "/api/comando/borrar_todo",
    "/api/comando/forzar_anomalia",
    "/api/dispositivo/SIM-999/comando/forzar_anomalia",
    "/api/dispositivo/SIM-001/comando/saturar_cpu",
    "/api/dispositivo/SIM-001/comando/borrar_todo",
])
def test_todo_lo_que_esta_fuera_de_las_listas_cerradas_no_existe(dashboard, ruta):
    servidor, controlador = dashboard

    status, _ = _pedir(servidor, ruta, metodo="POST", cabeceras=DEMO)

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
