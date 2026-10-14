# Práctica de Integración Hardware-Software-Firmware (HSF)

Prototipo que recorre las cuatro capas de un sistema informático — **hardware/firmware → sistema operativo → aplicación Python → persistencia/reporte** — construido para el segundo corte de *Integración de Sistemas de Información*, Universidad Santo Tomás.

Universidad Santo Tomás · Ingeniería en Informática
Estudiante: `[NombreEstudiante]` · Código: `[Codigo]` · Segundo corte 2026-2

**Demo en vivo en la nube:** <https://integration-corte2.duckdns.org>. Muestra los 3 dispositivos simulados en tiempo real, con los mismos controles por equipo: encender, apagar, reiniciar y fallos. Cómo está desplegada: [`deploy/DESPLIEGUE.md`](deploy/DESPLIEGUE.md).

## Qué hace

Un firmware simulado (proceso Python independiente, sin hardware físico) emite por un socket TCP telemetría de un dispositivo simulado: temperatura, humedad y vibración, con anomalías periódicas. Una aplicación Python modular se conecta, valida y clasifica cada lectura, consulta recursos del sistema operativo anfitrión, persiste los datos en CSV y genera un reporte de ejecución en JSON — todo sin detenerse ante errores de datos, caídas de conexión o fallas de escritura.

Ver el diagrama de arquitectura en [`diagramas/arquitectura_capas.svg`](diagramas/arquitectura_capas.svg) y el flujo de una lectura en [`diagramas/flujo_datos.svg`](diagramas/flujo_datos.svg).

## Estructura

```
DEMO.bat       doble clic: firmware + aplicación + dashboard en vivo (Windows)
hsf_app/       aplicación Python (adquisición, validación, procesamiento, SO, persistencia, orquestador)
hsf_app/web/   página del dashboard en vivo (HTML/JS sin dependencias externas)
firmware/      firmware simulado (servidor TCP, con comandos de mantenimiento por consola)
tests/         suite de pytest (TDD — 85 pruebas)
scripts/       demo end-to-end, generador de diagramas, herramientas de fallos controlados
diagramas/     arquitectura en capas y flujo de datos (SVG)
docs/          documento técnico, matriz de pruebas, fallos controlados, guion del video
data/          lecturas.csv y reporte_ejecucion.json (evidencia real de ejecución)
logs/          sistema.log (evidencia real de ejecución)
entrega/       plantillas de URL para la entrega en la plataforma de la universidad
```

## Demo en vivo con dashboard (la forma más fácil)

```bash
pip install -r requirements.txt
python -m hsf_app.demo          # en Windows también: doble clic en DEMO.bat
```

Simula **tres dispositivos a la vez**, cada uno con su propio proceso de firmware, puerto y ritmo de anomalías:

| Equipo | Nombre | Puerto |
|---|---|---|
| SIM-001 | Compresor | 8765 |
| SIM-002 | Bomba de agua | 8766 |
| SIM-003 | Motor de banda | 8767 |

La aplicación abre una conexión y un orquestador por equipo, cada uno en su hilo, y abre el dashboard en `http://127.0.0.1:8080`. El dashboard tiene dos vistas:

- **General:** toda la flota junta. Una tarjeta por equipo, gráficas con los tres superpuestos (cada equipo conserva su color en todas las vistas), indicadores del Anexo 3 §12 sumados, CPU, memoria y disco, y el registro de eventos de todos.
- **Por equipo (una pestaña cada uno):** última lectura, gráficas con su rango normal y anomalías, tabla, indicadores propios y sus **fallos controlados**: encender, apagar o reiniciar el equipo, enviar un dato corrupto, enviar un valor fuera de rango y forzar una anomalía.

Detener un equipo no afecta a los demás. Saturar la CPU queda como un botón general.

Los botones solo aceptan listas cerradas de comandos y de equipos, solo desde localhost y con una cabecera propia (protección contra CSRF y DNS rebinding). La demo escribe en `data/demo_*` y `logs/demo.log`, así que no toca la evidencia documentada. Se termina con Ctrl+C.

## Cómo correrlo por partes

```bash
python -m venv .venv && source .venv/bin/activate   # o .venv\Scripts\activate en PowerShell
pip install -r requirements.txt

# Terminal 1: firmware simulado
python firmware/firmware_simulador.py

# Terminal 2: aplicación (Ctrl+C para detener y generar el reporte final)
python -m hsf_app.app
```

O con el script de conveniencia (Linux/Git Bash: `scripts/ejecutar_demo.sh`; PowerShell: `scripts/ejecutar_demo.ps1`), o de forma acotada y reproducible con `python scripts/ejecutar_demo_acotado.py 20` (requiere el firmware ya corriendo).

## Pruebas

```bash
pip install -r requirements.txt
pytest tests/ -v
```

85 pruebas, todas con TDD (test primero, implementación después). Ver `docs/Matriz_Pruebas.md` para la trazabilidad contra los requisitos funcionales, y `docs/Fallos_Controlados.md` para los 6 fallos controlados ejecutados contra el sistema real.

## Documento técnico

El desarrollo completo (arquitectura, decisiones, resultados, indicadores y respuestas a las preguntas de la guía) está en [`docs/Documento_Tecnico_SegundoCorte.md`](docs/Documento_Tecnico_SegundoCorte.md) / `.docx`.
