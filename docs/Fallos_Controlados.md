# Fallos controlados — Práctica HSF (Anexo 3, §11)

Los 6 fallos que pide la guía, ejecutados de verdad contra el firmware simulado (`firmware/firmware_simulador.py`) corriendo como proceso independiente, o contra `scripts/servidor_fallas_simuladas.py` cuando el fallo necesita datos deliberadamente defectuosos. Ninguna de las salidas de abajo está inventada: son recortes reales de consola de las corridas hechas para este documento.

---

## 1. Desconectar o detener la fuente de datos (caso sin recuperación)

- **Causa**: se terminó el proceso del firmware simulado (`kill`) y no se volvió a levantar.
- **Síntoma**: cada intento de conexión nueva devuelve `WinError 10061` (conexión rechazada).
- **Detección**: `FuenteAdquisicion.conectar_con_reintentos` captura el `OSError` en cada intento y lo registra.
- **Respuesta**: reintenta con backoff creciente (3 intentos en esta corrida, configurable); al agotarlos, registra el error y termina de forma controlada — sin traceback — generando igual el reporte final.
- **Evidencia real**:

  ```
  19:52:56 | WARNING | reintentando conexión con el firmware (espera=0s): [WinError 10061] ...
  19:52:58 | WARNING | reintentando conexión con el firmware (espera=0.3s): [WinError 10061] ...
  19:53:01 | WARNING | reintentando conexión con el firmware (espera=0.3s): [WinError 10061] ...
  19:53:01 | ERROR   | no fue posible conectar con el firmware, se detiene la adquisición
  RESULTADO: {'lecturas_recibidas': 0, ..., 'desconexiones': 0, 'duracion_total_s': 6.73}
  ```

- **Mejora propuesta**: exponer un endpoint de salud (`/health`) o una métrica que un sistema de monitoreo externo pueda alertar tras N reintentos fallidos, en vez de solo registrar en el log local.

---

## 2. Enviar un dato con formato incorrecto

- **Causa**: el emisor (en esta prueba, `servidor_fallas_simuladas.py`) envía una línea que no es JSON válido.
- **Síntoma**: `json.loads` lanza `JSONDecodeError` al intentar interpretar la línea.
- **Detección**: `FuenteAdquisicion.leer_siguiente` convierte ese error en `ErrorAdquisicion`, una excepción propia y explícita.
- **Respuesta**: la app descarta esa única línea, cuenta `errores_adquisicion` y sigue leyendo la siguiente línea de la misma conexión sin reconectar (no fue una caída de enlace, fue un dato corrupto).
- **Evidencia real**:

  ```
  19:55:34 | WARNING | dato descartado por error de adquisición: línea corrupta recibida del firmware: Expecting value: line 1 column 1 (char 0)
  19:55:35 | INFO    | lectura normal de SIM-001 procesada
  ```

- **Mejora propuesta**: si la tasa de líneas corruptas supera un umbral (p. ej. 5 % de los eventos, el indicador del §12), tratarlo como señal de un problema de enlace físico y no solo de dato puntual.

---

## 3. Intentar escribir en una ruta sin permisos

- **Causa**: se configuró `ruta_csv` apuntando a una unidad que no existe en la máquina (`Z:\unidad_inexistente\lecturas.csv`), equivalente a una ruta sin acceso.
- **Síntoma**: `Path.mkdir`/`open` lanza `OSError` ([WinError 3] no se puede encontrar la ruta).
- **Detección**: el `try/except OSError` alrededor de `registrar_lectura_csv` en `hsf_app/app.py` lo captura en el punto exacto donde ocurre.
- **Respuesta**: se cuenta como `errores_persistencia`, se registra el error, y el ciclo principal **sigue corriendo** — la lectura ya validada no se pierde de vista, solo no queda en disco.
- **Evidencia real**:

  ```
  19:55:50 | ERROR | no se pudo persistir la lectura (ruta inaccesible): [WinError 3] El sistema no puede encontrar la ruta especificada: 'Z:\\'
  RESULTADO FALLO3: {..., 'errores_persistencia': 1, 'tasa_errores_pct': 100.0, ...}
  ```

- **Mejora propuesta**: si la persistencia primaria falla de forma sostenida, caer a una ruta secundaria (p. ej. el directorio temporal del usuario) en vez de solo descartar el dato.

> Nota de diseño: este fallo expuso un hueco real durante la construcción — antes de añadir el `try/except`, un fallo de escritura tumbaba toda la aplicación, violando el RF09. Se corrigió con una prueba (`test_ejecutar_continua_si_falla_la_persistencia`) antes de tocar el código, siguiendo TDD.

---

## 4. Introducir una variable fuera del rango esperado

- **Causa**: el emisor envía `humedad_pct=250.0`, fuera del rango físicamente válido (0–100 %).
- **Síntoma**: ninguno a nivel de transporte — el JSON es válido, el problema es semántico.
- **Detección**: `validar_lectura` compara contra `RANGOS_VALIDOS` en `hsf_app/config.py` y lanza `ErrorValidacion`.
- **Respuesta**: se descarta la lectura, se cuenta `errores_validacion`, no se persiste, el ciclo continúa.
- **Evidencia real**:

  ```
  19:55:35 | WARNING | lectura descartada por validación: humedad_pct fuera de rango válido: 250.0 no está en [0.0, 100.0]
  ```

- **Mejora propuesta**: distinguir "fuera de rango por error de sensor" de "fuera de rango por sensor dañado" llevando un contador por variable, no solo global, para poder apuntar a qué sensor revisar primero.

---

## 5. Simular saturación de CPU o memoria

- **Causa**: se lanzaron procesos de cómputo intensivo (`scripts/simular_saturacion_recursos.py`, uno por núcleo lógico) durante 4 segundos.
- **Síntoma**: el uso de CPU del sistema sube de forma medible mientras la saturación está activa.
- **Detección**: `hsf_app/os_resources.obtener_snapshot_recursos` usa `psutil.cpu_percent()`, que mide a nivel de todo el sistema operativo, no solo del proceso de la app.
- **Respuesta**: la consulta de recursos del SO (RF06) no depende de que la CPU esté libre — sigue devolviendo una lectura válida (más alta) en vez de fallar o colgarse.
- **Evidencia real** (antes / durante / después, mismo proceso, misma máquina):

  ```
  ANTES:   cpu_percent = 25.0
  DURANTE: cpu_percent = 93.9   (con 20 procesos saturadores)
  DESPUÉS: cpu_percent = 0.0
  ```

- **Mejora propuesta**: si `cpu_percent` supera un umbral sostenido durante varios ciclos, alargar el intervalo de lectura para no competir por CPU con el propio sistema que se está monitoreando.

---

## 6. Interrumpir temporalmente la red o el puerto de comunicación

- **Causa**: se mató el proceso del firmware a mitad de una corrida de 40 lecturas, y se volvió a levantar ~2.5 s después en el mismo puerto.
- **Síntoma**: la lectura en curso falla con `WinError 10054` (conexión reiniciada por el host remoto); el primer intento de reconexión inmediato falla con `WinError 10061` porque el firmware todavía no estaba arriba.
- **Detección**: `FuenteAdquisicion._leer_linea_cruda` detecta el `recv()` vacío/erróneo y lo traduce a `ConnectionError`; el orquestador lo distingue de un dato corrupto y dispara `conectar_con_reintentos`.
- **Respuesta**: reintenta con backoff creciente; en cuanto el firmware vuelve a aceptar conexiones, retoma la lectura normal — sin reiniciar el proceso de la app ni perder las métricas acumuladas hasta ese punto.
- **Evidencia real**:

  ```
  19:55:00 | ERROR   | se perdió la conexión con el firmware: [WinError 10054] ...
  19:55:02 | WARNING | reintentando conexión con el firmware (espera=0s): [WinError 10061] ...
  19:55:04 | INFO    | conexión recuperada con el firmware
  19:55:04 | INFO    | lectura normal de SIM-001 procesada
  ...
  RESULTADO FALLO6: {'lecturas_recibidas': 40, 'lecturas_validas': 40, ..., 'desconexiones': 1,
                      'tiempo_recuperacion_promedio_s': 3.57, 'duracion_total_s': 42.55}
  ```

  La corrida completó sus 40 lecturas esperadas pese a la interrupción real de ~3.5 s — el indicador de "tiempo de recuperación" del §12 queda medido con un dato real, no estimado.

- **Mejora propuesta**: si el tiempo de recuperación promedio sube de corrida en corrida, es señal de que el enlace se está degradando y conviene alertar antes de que se vuelva una desconexión permanente (fallo 1).

---

Fuente: el autor — todas las salidas de consola citadas arriba son recortes literales de ejecuciones reales de este repositorio, no texto inventado para la entrega.

---

## Reproducirlos en vivo y hallazgos adicionales

La demo (`python -m hsf_app.demo` o `DEMO.bat`) reproduce cinco de estos fallos con un botón del dashboard: detener y reiniciar el firmware (fallos 1 y 6), dato corrupto (2), valor fuera de rango (4) y saturación de CPU (5). El fallo 3 queda cubierto por su prueba automática y la corrida documentada arriba.

Como la demo simula tres equipos a la vez, los fallos de firmware se disparan **sobre un solo equipo** desde su pestaña, y eso muestra además el aislamiento entre equipos. En la prueba en vivo, con SIM-002 detenido, el dashboard pasó a "2 de 3 equipos conectados" y SIM-001 y SIM-003 siguieron recibiendo (de 76 a 79 lecturas). Al reiniciarlo, SIM-002 se reconectó solo (TP-11).

Al construir la demo aparecieron tres defectos reales más. Cada uno se cubrió primero con una prueba que fallaba:

- **Firmware colgado:** si el firmware dejaba de enviar sin cerrar la conexión, `recv()` lanzaba `TimeoutError`, que no es `ConnectionError`, y tumbaba la aplicación. Ahora se trata como una caída y se reconecta (TP-09).
- **Dos firmwares en el mismo puerto (solo Windows):** con `SO_REUSEADDR`, Windows deja que un segundo proceso escuche el mismo puerto, y las conexiones van a cualquiera de los dos. Linux lo impide. La opción ahora solo se usa fuera de Windows.
- **CPU siempre en 0 %:** `psutil.cpu_percent()` recuerda la medición anterior por hilo, y el servidor del dashboard atiende cada petición en un hilo nuevo. Ahora la CPU se mide en un único hilo dedicado.
