# Guion del video — Segundo corte (Anexo 3 §13 + Anexo 5)

Duración objetivo: **15:00 exactos como máximo**. Grabar con tomas del rostro explicando (obligatorio, Anexo 5.e). Usar la plantilla `.ppt` del escritorio virtual del docente para las diapositivas (Anexo 5.a) — este guion da el contenido de cada una, no el diseño.

Nombre del archivo final (el `.txt` con la URL de YouTube): `Programa_NombreEstudiante_Codigo_2_Corte.txt`.

---

| # | Bloque | Minutaje | Qué mostrar en pantalla |
|---|---|---|---|
| 1 | Portada y datos personales | 0:00–0:45 | Diapositiva con nombre, universidad, programa, "Entrega dos — Práctica HSF", fecha actual. Rostro a cámara. |
| 2 | Contexto y arquitectura | 0:45–2:00 | `diagramas/arquitectura_capas.svg` y `diagramas/flujo_datos.svg` en pantalla completa |
| 3 | Repositorio y README | 2:00–3:30 | GitHub abierto: estructura de carpetas, `README.md` renderizado |
| 4 | Firmware simulado en ejecución | 3:30–5:00 | Terminal con `python firmware/firmware_simulador.py` corriendo, tramas JSON visibles |
| 5 | Aplicación Python modular | 5:00–7:00 | Editor con `hsf_app/` abierto: recorrer `acquisition.py`, `validation.py`, `processing.py`, `app.py` señalando una responsabilidad por archivo |
| 6 | Datos y reporte generados | 7:00–8:30 | `data/lecturas.csv` y `data/reporte_ejecucion.json` reales abiertos, señalando una lectura normal y una anómala |
| 7 | Matriz de pruebas | 8:30–10:00 | `docs/Matriz_Pruebas.md` + terminal con `pytest tests/ -v` corriendo en vivo (28 en verde) |
| 8 | Logs y fallos controlados | 10:00–11:30 | `logs/sistema.log` + un fragmento de `docs/Fallos_Controlados.md` (sugerido: fallo 6, reconexión real) |
| 9 | Preguntas de integración | 11:30–13:30 | Diapositiva con las 13 preguntas; responder cada una en 1 frase, remitiendo al documento técnico §8 para el detalle |
| 10 | Conclusiones | 13:30–14:30 | Diapositiva de cierre con las 2 conclusiones del documento técnico §9 |
| 11 | Referencias APA 7 | 14:30–15:00 | Diapositiva con las 4 referencias del documento técnico §10 |

## Lista de control antes de grabar

- [ ] Firmware y app corriendo de verdad en pantalla (no capturas estáticas) en los bloques 4, 5 y 7.
- [ ] Rostro visible explicando en cámara en algún punto de cada bloque, no solo al inicio.
- [ ] Plantilla `.ppt` del docente aplicada a las diapositivas.
- [ ] Reemplazar `[NombreEstudiante]`, `[Codigo]` y la fecha en la diapositiva de portada.
- [ ] Tiempo total ≤ 15:00 (cronometrar un ensayo antes de la grabación final).
- [ ] Verificar en ventana de incógnito que el video publicado en YouTube es visible sin iniciar sesión, o que el docente tiene acceso explícito.
