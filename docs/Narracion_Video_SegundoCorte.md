# Narración palabra por palabra — Video Segundo Corte

Leer en voz natural, no apurada. Los tiempos son orientativos (≈150 palabras/min); si un bloque se alarga, recortar ejemplos, no las frases que responden directamente a una pregunta obligatoria del Anexo 3.

---

## Bloque 1 — Portada (0:00–0:45)

"Hola, mi nombre es [NombreEstudiante], estudiante de Ingeniería en Informática en la Universidad Santo Tomás, código [Codigo]. Este es el video de la entrega dos: la práctica de integración hardware, software y firmware, del segundo corte de Integración de Sistemas de Información. Hoy es [fecha]. En los próximos minutos voy a mostrar el prototipo completo, en ejecución real, no simulado a mano, y voy a responder las preguntas de integración que pide la guía."

## Bloque 2 — Contexto y arquitectura (0:45–2:00)

"El prototipo recorre las cuatro capas de un sistema informático: hardware, firmware, sistema operativo y software de aplicación. No tuve una placa física disponible, así que el firmware está completamente simulado en Python — una decisión que justifico en el documento técnico, pero que en resumen elegí porque corre igual en cualquier máquina, sin depender de que una placa conecte bien justo el día de esta grabación. Este es el diagrama de capas: el firmware simulado emite datos por un socket TCP, el sistema operativo expone ese socket además de memoria, disco y procesos, y mi aplicación Python valida, clasifica, persiste y reporta. Y este es el flujo de una lectura individual: desde que el firmware la genera hasta que queda en el CSV y en el reporte, pasando por validación y clasificación — y marcado el punto exacto donde, si algo falla, la aplicación sigue corriendo en vez de caerse."

## Bloque 3 — Repositorio y README (2:00–3:30)

"Este es el repositorio en GitHub. La estructura separa claramente la aplicación en `hsf_app`, el firmware simulado, las pruebas, los scripts de demo, los diagramas y la documentación. El README explica cómo instalar las dependencias y cómo correr el sistema completo, con dos terminales: una para el firmware y otra para la aplicación. Todo lo que voy a mostrar en este video se puede reproducir exactamente con estos comandos, en Windows o en Linux."

## Bloque 4 — Firmware simulado en ejecución (3:30–5:00)

"Con un doble clic en DEMO.bat se levantan el firmware, la aplicación y este panel de monitoreo. Acá tengo el firmware simulado corriendo de verdad, no una captura de pantalla. Es un servidor TCP que escucha en el puerto 8765 y, cada segundo, emite una trama JSON con el identificador del dispositivo, temperatura, humedad y vibración. Cada siete ciclos, inyecta deliberadamente una anomalía en una de las tres variables, para que la aplicación tenga algo real que clasificar como condición anómala. Todo esto corre con la librería estándar de Python, sin ninguna dependencia externa ni hardware."

## Bloque 5 — Aplicación Python modular (5:00–7:00)

"La aplicación está dividida en módulos con una responsabilidad cada uno, no en un único script. `acquisition.py` se conecta al firmware por socket y maneja la reconexión si se pierde la conexión. `validation.py` revisa que cada lectura tenga la estructura, el tipo y el rango correctos. `processing.py` clasifica cada lectura como normal o anómala comparando contra umbrales operativos. `os_resources.py` consulta CPU, memoria, disco y variables de entorno del sistema operativo anfitrión. Y `app.py` orquesta todo ese ciclo: lee, valida, clasifica, persiste, y nunca deja que un error de comunicación, de dato o de escritura tumbe la aplicación completa — eso es exactamente lo que pide el requisito de recuperarse de una falla sin perder el control, y lo voy a demostrar en vivo más adelante con los fallos controlados."

## Bloque 6 — Datos y reporte generados (7:00–8:30)

"Esta es una corrida real de veinte lecturas. En el CSV se ve cada lectura con su marca de tiempo y su estado: la mayoría normales, y dos marcadas como anómalas, exactamente las que el firmware inyectó a propósito. Y este es el reporte de ejecución en JSON: trae las métricas agregadas — lecturas válidas, anómalas, errores — y además un snapshot real de los recursos del sistema operativo en el momento del cierre: uso de CPU, memoria, disco y el PID del proceso. Ningún dato de este reporte está inventado, es la salida real de haber corrido el sistema."

## Bloque 7 — Matriz de pruebas (8:30–10:00)

"El proyecto tiene sesenta y cuatro pruebas automáticas con pytest, escritas con test primero, implementación después — es decir, TDD real. Las voy a correr ahora mismo [ejecutar `pytest tests/ -v` en pantalla]. Como se ve, las sesenta y cuatro pasan. La matriz de pruebas del documento técnico cruza cada requisito funcional con su prueba automática y, cuando corresponde, con una corrida manual real contra el sistema completo — no son pruebas teóricas, son pruebas que de verdad se ejecutaron."

## Bloque 8 — Fallos controlados en vivo (10:00–11:00)

"Ahora lo más importante: qué pasa cuando algo falla. Desde este panel provoco fallos reales. Fuerzo una anomalía y aparece el punto rojo. Mando un dato corrupto y un valor fuera de rango: suben los contadores, y el sistema sigue leyendo. Ahora detengo el firmware: el estado pasa a reconectando y en el registro se ven los reintentos con espera creciente. Lo reinicio, y la aplicación se reconecta sola, sin reiniciarla. Por último saturo la CPU: la gráfica sube casi al cien por ciento y la integración sigue funcionando. Estos seis fallos, con su salida de consola real, están documentados en el repositorio."

## Bloque 8b — Indicadores técnicos (11:00–11:30)

"Con todas esas corridas medí los indicadores que pide la guía. La disponibilidad de comunicación fue de noventa y siete coma seis por ciento, incluso con una caída real del enlace. La latencia promedio fue de un cuarto de milisegundo, sobre la misma máquina. El noventa y ocho coma cuatro por ciento de los datos recibidos fueron válidos, y el tiempo de recuperación tras la caída fue de tres coma cinco segundos. La tasa de errores agregada queda en seis por ciento, pero solo porque incluye las corridas donde inyecté fallos a propósito: en operación normal fue cero."

## Bloque 9 — Preguntas de integración (11:30–13:30)

"Voy a responder, en una frase cada una, las preguntas de integración que pide la guía; el desarrollo completo de cada una está en el documento técnico, sección ocho.

Uno: el hardware ejecuta y ofrece recursos; el firmware decide qué dato generar y cuándo; cada transformación ocurre en una frontera distinta, desde el firmware hasta la persistencia.

Dos: la aplicación usa sockets TCP, sistema de archivos y consultas de CPU, memoria, disco y variables de entorno.

Tres: si el sistema operativo revoca un permiso, la escritura lanza una excepción que mi aplicación captura, cuenta como error y sigue corriendo — lo demostré en vivo en el bloque anterior.

Cuatro: Python da velocidad de desarrollo y manejo de errores expresivo, pero el GIL le impide paralelismo real de CPU, y no sirve para programar firmware de bajo nivel.

Cinco: lo que exige temporización estricta va en firmware; lo que exige lógica de negocio y mantenibilidad va en software de aplicación.

Seis: con cien dispositivos simultáneos, necesitaría un servidor asíncrono y probablemente una cola de mensajes en vez de sockets directos.

Siete: el riesgo principal es tratar el dato externo como código; por eso solo lo parseo como JSON y lo valido campo por campo, nunca lo ejecuto.

Ocho: la integridad se garantiza con marca de tiempo y estado en cada registro, más logs con evento y resultado.

Nueve: los mensajes de error de socket difieren entre Windows y Linux, aunque Python los normaliza a la misma jerarquía de excepciones.

Diez: actualizaría el firmware con una estrategia azul-verde, validando la versión nueva antes de conmutar el tráfico real.

Once: antes de producción, aplicaría pruebas de carga sostenida, de seguridad y de concurrencia real con varios dispositivos.

Doce: el punto único de falla es el socket hacia un único firmware; lo volvería tolerante con redundancia y una cola intermedia entre adquisición y persistencia."

## Bloque 10 — Conclusiones (13:30–14:30)

"Para cerrar: este prototipo demuestra, con evidencia real y no simulada a mano, el recorrido completo que pide la guía, desde el dato que genera el firmware hasta el reporte final, pasando por servicios reales del sistema operativo. La disciplina de pruebas primero no fue un formalismo: encontró un defecto real de tolerancia a fallas antes de la entrega, que corregí antes de grabar este video. Y los seis fallos controlados, ejecutados contra procesos reales, confirman que el sistema cumple el requisito de no perder el control ante una falla. La limitación más clara es la escala: hoy funciona para un dispositivo a la vez, y ahí es donde apuntaría el siguiente esfuerzo de ingeniería."

## Bloque 11 — Referencias APA 7 (14:30–15:00)

"Las referencias de este trabajo son: la guía de la práctica de Martínez Barrera, del Aula Virtual de la Universidad Santo Tomás; la documentación oficial de Python, específicamente los módulos socket, json, logging y multiprocessing; la documentación de la librería psutil; y la documentación de Microsoft sobre los códigos de error de Windows Sockets. Todas estas referencias están completas, en formato APA séptima edición, en el documento técnico. Muchas gracias."
