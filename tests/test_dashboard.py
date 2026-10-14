import http.client
import json
import threading

import pytest

from hsf_app.config import Dispositivo
from hsf_app.dashboard import RECURSOS_VISIBLES, crear_servidor_dashboard
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


@pytest.mark.parametrize("ruta", ["/?fbclid=abc123", "/api/estado?t=1"])
def test_un_query_string_no_rompe_las_rutas(dashboard, ruta):
    # Los enlaces compartidos en redes sociales llegan con ?fbclid=... pegado.
    servidor, _ = dashboard

    status, _ = _pedir(servidor, ruta)

    assert status == 200


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


@pytest.fixture
def dashboard_publico():
    controlador = ControladorFalso()
    flota = EstadoFlota([(COMPRESOR, EstadoIntegracion())])
    servidor = crear_servidor_dashboard(
        flota, controlador, puerto=0, muestreador_cpu=MuestreadorFalso(),
        hosts_publicos=("demo.example.org",), solo_lectura=True,
    )
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield servidor, controlador
    servidor.shutdown()
    servidor.server_close()


def test_el_host_publico_configurado_es_aceptado(dashboard_publico):
    servidor, _ = dashboard_publico

    status, _ = _pedir(servidor, "/api/estado", cabeceras={"Host": "demo.example.org"})

    assert status == 200


def test_un_host_publico_no_configurado_sigue_rechazado(dashboard_publico):
    servidor, _ = dashboard_publico

    status, _ = _pedir(servidor, "/api/estado", cabeceras={"Host": "otro.example.org"})

    assert status == 403


def test_en_solo_lectura_los_comandos_se_rechazan(dashboard_publico):
    servidor, controlador = dashboard_publico

    status, _ = _pedir(servidor, "/api/dispositivo/SIM-001/comando/forzar_anomalia", metodo="POST", cabeceras=DEMO)

    assert status == 403
    assert controlador.ejecutados == []


def test_en_solo_lectura_no_se_ofrecen_comandos(dashboard_publico):
    servidor, _ = dashboard_publico

    datos = json.loads(_pedir(servidor, "/api/estado")[1])

    assert datos["solo_lectura"] is True
    assert datos["comandos_globales"] == []
    assert datos["comandos_dispositivo"] == []


def test_ruta_desconocida_da_404(dashboard):
    servidor, _ = dashboard

    status, _ = _pedir(servidor, "/no-existe")

    assert status == 404


def _descargar(servidor, ruta, cabeceras=None):
    conexion = http.client.HTTPConnection("127.0.0.1", servidor.server_address[1], timeout=3)
    try:
        conexion.request("GET", ruta, headers=cabeceras or {})
        respuesta = conexion.getresponse()
        return respuesta.status, respuesta.getheader("Content-Disposition", ""), respuesta.read()
    finally:
        conexion.close()


def test_el_reporte_se_descarga_como_archivo_json(dashboard):
    servidor, _ = dashboard

    status, disposicion, cuerpo = _descargar(servidor, "/api/reporte")

    reporte = json.loads(cuerpo)
    assert status == 200
    assert disposicion.startswith('attachment; filename="reporte_hsf_') and disposicion.endswith('.json"')
    assert reporte["generado"].endswith("+00:00")
    assert reporte["general"]["total"] == 1
    assert reporte["dispositivos"][0]["id"] == "SIM-001"
    assert reporte["recursos_sistema_operativo"]["cpu_percent"] == 37.5


def test_el_reporte_no_expone_mas_que_el_panel(dashboard):
    # Es público en la nube: nada de variables de entorno ni la serie completa de lecturas.
    servidor, _ = dashboard

    reporte = json.loads(_descargar(servidor, "/api/reporte")[2])

    assert set(reporte["recursos_sistema_operativo"]) == set(RECURSOS_VISIBLES)
    assert "lecturas" not in reporte["dispositivos"][0]


def test_en_solo_lectura_el_reporte_sigue_disponible(dashboard_publico):
    servidor, _ = dashboard_publico

    status, _, _ = _descargar(servidor, "/api/reporte", cabeceras={"Host": "demo.example.org"})

    assert status == 200
