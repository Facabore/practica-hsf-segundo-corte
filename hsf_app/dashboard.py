"""Servidor HTTP del dashboard en vivo, solo con la librería estándar.

Expone cinco rutas:
  GET  /                                        la página del dashboard
  GET  /api/estado                              snapshot de la flota + recursos del SO (JSON)
  GET  /api/reporte                             reporte de ejecución en el momento, como archivo .json
  POST /api/comando/<nombre>                    fallo controlado global (p. ej. saturar CPU)
  POST /api/dispositivo/<id>/comando/<nombre>   fallo controlado sobre un solo equipo

Seguridad (pregunta de la guía sobre ejecutar comandos del sistema):
  - escucha solo en 127.0.0.1;
  - comandos e ids de dispositivo son listas cerradas que define el
    controlador; lo que llega en la URL nunca se ejecuta ni se interpola,
    solo se busca en esas listas;
  - los POST exigen la cabecera X-HSF-Demo, que un sitio web ajeno no puede
    enviar sin permiso CORS (que este servidor nunca concede);
  - se rechaza todo Host que no sea localhost, contra DNS rebinding.
"""

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from hsf_app.config import RANGOS_NORMALES
from hsf_app.os_resources import obtener_snapshot_recursos

PAGINA = Path(__file__).resolve().parent / "web" / "dashboard.html"
CABECERA_DEMO = "X-HSF-Demo"
RECURSOS_VISIBLES = ("cpu_percent", "memoria_percent", "disco_percent", "sistema_operativo", "proceso_pid")


class _Manejador(BaseHTTPRequestHandler):
    server: "ServidorDashboard"

    def _host_permitido(self) -> bool:
        puerto = self.server.server_address[1]
        permitidos = (f"127.0.0.1:{puerto}", f"localhost:{puerto}", *self.server.hosts_publicos)
        return self.headers.get("Host", "") in permitidos

    def _ruta(self) -> str:
        # Sin query string: los enlaces compartidos llegan con ?fbclid=... y similares.
        return urlsplit(self.path).path

    def _responder(self, status: int, cuerpo: bytes, tipo: str, descarga: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        if descarga:
            self.send_header("Content-Disposition", f'attachment; filename="{descarga}"')
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, status: int, datos: dict) -> None:
        self._responder(status, json.dumps(datos, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        if not self._host_permitido():
            return self._json(403, {"ok": False, "mensaje": "host no permitido"})
        ruta = self._ruta()
        if ruta in ("/", "/index.html"):
            return self._responder(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
        if ruta == "/api/estado":
            return self._json(200, self.server.armar_estado())
        if ruta == "/api/reporte":
            reporte = self.server.armar_reporte()
            cuerpo = json.dumps(reporte, indent=2, ensure_ascii=False).encode("utf-8")
            nombre = f"reporte_hsf_{datetime.now(timezone.utc):%Y%m%d-%H%M%S}_UTC.json"
            return self._responder(200, cuerpo, "application/json; charset=utf-8", descarga=nombre)
        self._json(404, {"ok": False, "mensaje": "ruta no encontrada"})

    def do_POST(self) -> None:
        if self.server.solo_lectura:
            return self._json(403, {"ok": False, "mensaje": "modo solo lectura: los fallos se disparan desde la demo local"})
        if not self._host_permitido() or self.headers.get(CABECERA_DEMO) != "1":
            return self._json(403, {"ok": False, "mensaje": "solicitud no permitida"})
        controlador = self.server.controlador
        partes = self._ruta().strip("/").split("/")
        if len(partes) == 3 and partes[:2] == ["api", "comando"] and partes[2] in controlador.comandos_globales:
            return self._json(200, {"ok": True, "mensaje": controlador.ejecutar(partes[2])})
        if (
            len(partes) == 5
            and partes[0:2] == ["api", "dispositivo"]
            and partes[3] == "comando"
            and partes[2] in controlador.dispositivos
            and partes[4] in controlador.comandos_dispositivo
        ):
            return self._json(200, {"ok": True, "mensaje": controlador.ejecutar(partes[4], partes[2])})
        self._json(404, {"ok": False, "mensaje": "comando o dispositivo inexistente"})

    def log_message(self, formato, *args) -> None:
        pass  # el dashboard consulta cada segundo; no ensuciar la consola


class ServidorDashboard(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, direccion, estado, controlador, muestreador_cpu=None, hosts_publicos=(), solo_lectura=False):
        super().__init__(direccion, _Manejador)
        self.estado = estado
        self.controlador = controlador
        self.muestreador_cpu = muestreador_cpu
        # Dominios con los que llega el tráfico desde el proxy (p. ej. Caddy).
        self.hosts_publicos = tuple(hosts_publicos)
        # Publicado en internet: se ve todo, pero nadie puede disparar fallos.
        self.solo_lectura = solo_lectura

    def armar_estado(self) -> dict:
        datos = self.estado.snapshot()
        recursos = obtener_snapshot_recursos()
        datos["recursos"] = {clave: recursos.get(clave) for clave in RECURSOS_VISIBLES}
        if self.muestreador_cpu is not None:
            # Cada petición llega en un hilo nuevo: la CPU se lee del muestreador dedicado.
            datos["recursos"]["cpu_percent"] = self.muestreador_cpu.ultimo
        datos["rangos_normales"] = {variable: list(rango) for variable, rango in RANGOS_NORMALES.items()}
        datos["solo_lectura"] = self.solo_lectura
        datos["comandos_globales"] = [] if self.solo_lectura else _listar(self.controlador.comandos_globales)
        datos["comandos_dispositivo"] = [] if self.solo_lectura else _listar(self.controlador.comandos_dispositivo)
        return datos

    def armar_reporte(self) -> dict:
        """Reporte de ejecución (RF08) generado en el momento, sin esperar al cierre.

        Toma lo mismo que muestra el panel: ni variables de entorno ni la serie de lecturas.
        """
        datos = self.armar_estado()
        return {
            "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tipo": "reporte parcial en vivo: la ejecución sigue en curso",
            "segundos_activo": datos["segundos_activo"],
            "general": datos["general"],
            "dispositivos": [
                {clave: valor for clave, valor in equipo.items() if clave != "lecturas"}
                for equipo in datos["dispositivos"]
            ],
            "recursos_sistema_operativo": datos["recursos"],
        }


def _listar(comandos: dict) -> list[dict]:
    return [
        {"nombre": nombre, "etiqueta": etiqueta, "descripcion": descripcion}
        for nombre, (etiqueta, descripcion) in comandos.items()
    ]


def crear_servidor_dashboard(
    estado,
    controlador,
    host: str = "127.0.0.1",
    puerto: int = 8080,
    muestreador_cpu=None,
    hosts_publicos=(),
    solo_lectura: bool = False,
) -> ServidorDashboard:
    return ServidorDashboard((host, puerto), estado, controlador, muestreador_cpu, hosts_publicos, solo_lectura)
