"""Servidor HTTP del dashboard en vivo, solo con la librería estándar.

Expone tres rutas:
  GET  /                      la página del dashboard
  GET  /api/estado            snapshot del estado + recursos del SO (JSON)
  POST /api/comando/<nombre>  dispara un fallo controlado de la demo

Seguridad (pregunta de la guía sobre ejecutar comandos del sistema):
  - escucha solo en 127.0.0.1;
  - los comandos son una lista cerrada que define el controlador; el nombre
    de la URL nunca se ejecuta ni se interpola, solo se busca en esa lista;
  - los POST exigen la cabecera X-HSF-Demo, que un sitio web ajeno no puede
    enviar sin permiso CORS (que este servidor nunca concede);
  - se rechaza todo Host que no sea localhost, contra DNS rebinding.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hsf_app.config import RANGOS_NORMALES
from hsf_app.os_resources import obtener_snapshot_recursos

PAGINA = Path(__file__).resolve().parent / "web" / "dashboard.html"
CABECERA_DEMO = "X-HSF-Demo"
RECURSOS_VISIBLES = ("cpu_percent", "memoria_percent", "disco_percent", "sistema_operativo", "proceso_pid")


class _Manejador(BaseHTTPRequestHandler):
    server: "ServidorDashboard"

    def _host_permitido(self) -> bool:
        puerto = self.server.server_address[1]
        return self.headers.get("Host", "") in (f"127.0.0.1:{puerto}", f"localhost:{puerto}")

    def _responder(self, status: int, cuerpo: bytes, tipo: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, status: int, datos: dict) -> None:
        self._responder(status, json.dumps(datos, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        if not self._host_permitido():
            return self._json(403, {"ok": False, "mensaje": "host no permitido"})
        if self.path in ("/", "/index.html"):
            return self._responder(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/estado":
            return self._json(200, self.server.armar_estado())
        self._json(404, {"ok": False, "mensaje": "ruta no encontrada"})

    def do_POST(self) -> None:
        if not self._host_permitido() or self.headers.get(CABECERA_DEMO) != "1":
            return self._json(403, {"ok": False, "mensaje": "solicitud no permitida"})
        prefijo = "/api/comando/"
        nombre = self.path[len(prefijo):] if self.path.startswith(prefijo) else None
        if nombre not in self.server.controlador.comandos:
            return self._json(404, {"ok": False, "mensaje": "comando inexistente"})
        mensaje = self.server.controlador.ejecutar(nombre)
        self._json(200, {"ok": True, "mensaje": mensaje})

    def log_message(self, formato, *args) -> None:
        pass  # el dashboard consulta cada segundo; no ensuciar la consola


class ServidorDashboard(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, direccion, estado, controlador, muestreador_cpu=None):
        super().__init__(direccion, _Manejador)
        self.estado = estado
        self.controlador = controlador
        self.muestreador_cpu = muestreador_cpu

    def armar_estado(self) -> dict:
        datos = self.estado.snapshot()
        recursos = obtener_snapshot_recursos()
        datos["recursos"] = {clave: recursos.get(clave) for clave in RECURSOS_VISIBLES}
        if self.muestreador_cpu is not None:
            # Cada petición llega en un hilo nuevo: la CPU se lee del muestreador dedicado.
            datos["recursos"]["cpu_percent"] = self.muestreador_cpu.ultimo
        datos["rangos_normales"] = {variable: list(rango) for variable, rango in RANGOS_NORMALES.items()}
        datos["comandos"] = [
            {"nombre": nombre, "etiqueta": etiqueta, "descripcion": descripcion}
            for nombre, (etiqueta, descripcion) in self.controlador.comandos.items()
        ]
        return datos


def crear_servidor_dashboard(estado, controlador, host: str = "127.0.0.1", puerto: int = 8080, muestreador_cpu=None) -> ServidorDashboard:
    return ServidorDashboard((host, puerto), estado, controlador, muestreador_cpu)
