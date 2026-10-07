# Práctica de Integración Hardware-Software-Firmware (HSF)

Prototipo que recorre las cuatro capas de un sistema informático — **hardware/firmware → sistema operativo → aplicación Python → persistencia/reporte** — construido para el segundo corte de *Integración de Sistemas de Información*, Universidad Santo Tomás.

Universidad Santo Tomás · Ingeniería en Informática
Estudiante: `[NombreEstudiante]` · Código: `[Codigo]` · Segundo corte 2026-2

## Qué hace

Un firmware simulado (proceso Python independiente, sin hardware físico) emite por un socket TCP telemetría de un dispositivo simulado: temperatura, humedad y vibración, con anomalías periódicas. Una aplicación Python modular se conecta, valida y clasifica cada lectura, consulta recursos del sistema operativo anfitrión, persiste los datos en CSV y genera un reporte de ejecución en JSON — todo sin detenerse ante errores de datos, caídas de conexión o fallas de escritura.

Ver el diagrama de arquitectura en [`diagramas/arquitectura_capas.svg`](diagramas/arquitectura_capas.svg) y el flujo de una lectura en [`diagramas/flujo_datos.svg`](diagramas/flujo_datos.svg).

## Estructura

```
hsf_app/       aplicación Python (adquisición, validación, procesamiento, SO, persistencia, orquestador)
firmware/      firmware simulado (servidor TCP)
tests/         suite de pytest (TDD — 27 pruebas)
scripts/       demo end-to-end, generador de diagramas, herramientas de fallos controlados
diagramas/     arquitectura en capas y flujo de datos (SVG)
docs/          documento técnico, matriz de pruebas, fallos controlados, guion del video
data/          lecturas.csv y reporte_ejecucion.json (evidencia real de ejecución)
logs/          sistema.log (evidencia real de ejecución)
entrega/       plantillas de URL para la entrega en la plataforma de la universidad
```

## Cómo correrlo

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

27 pruebas, todas con TDD (test primero, implementación después). Ver `docs/Matriz_Pruebas.md` para la trazabilidad contra los requisitos funcionales, y `docs/Fallos_Controlados.md` para los 6 fallos controlados ejecutados contra el sistema real.

## Documento técnico

El desarrollo completo (arquitectura, decisiones, resultados, indicadores y respuestas a las preguntas de la guía) está en [`docs/Documento_Tecnico_SegundoCorte.md`](docs/Documento_Tecnico_SegundoCorte.md) / `.docx`.
