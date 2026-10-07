"""Genera versiones PNG de los diagramas de arquitectura, para incrustar en
el documento técnico .docx (Word no soporta SVG de forma nativa en todas
las versiones). Las versiones SVG en `diagramas/` siguen siendo la fuente
vectorial para el repositorio y el video; este script solo rasteriza.

Uso: python scripts/generar_diagramas_png.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SALIDA = Path(__file__).resolve().parent.parent / "diagramas"
ESCALA = 2

COLOR_HARDWARE = "#8d6e63"
COLOR_FIRMWARE = "#ef6c00"
COLOR_SO = "#5e35b1"
COLOR_PYTHON = "#1565c0"
COLOR_DATOS = "#2e7d32"
COLOR_TEXTO = "#1a1a1a"
COLOR_BLANCO = "#ffffff"
COLOR_FLECHA = "#555555"
COLOR_PIE = "#777777"


def _fuente(tam: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    nombre = "segoeuib.ttf" if negrita else "segoeui.ttf"
    try:
        return ImageFont.truetype(f"C:/Windows/Fonts/{nombre}", tam)
    except OSError:
        return ImageFont.load_default()


def _texto_centrado(draw, cx, y, texto, fuente, color):
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    ancho = bbox[2] - bbox[0]
    draw.text((cx - ancho / 2, y), texto, font=fuente, fill=color)


def _caja(draw, x, y, ancho, alto, color, titulo, subtitulo=""):
    draw.rounded_rectangle([x, y, x + ancho, y + alto], radius=10 * ESCALA, fill=color)
    cx = x + ancho / 2
    fuente_titulo = _fuente(16 * ESCALA, negrita=True)
    fuente_sub = _fuente(12 * ESCALA)
    if subtitulo:
        _texto_centrado(draw, cx, y + alto / 2 - 20 * ESCALA, titulo, fuente_titulo, COLOR_BLANCO)
        _texto_centrado(draw, cx, y + alto / 2 + 4 * ESCALA, subtitulo, fuente_sub, COLOR_BLANCO)
    else:
        _texto_centrado(draw, cx, y + alto / 2 - 10 * ESCALA, titulo, fuente_titulo, COLOR_BLANCO)


def _flecha_vertical(draw, x, y1, y2):
    draw.line([x, y1, x, y2], fill=COLOR_FLECHA, width=int(2.5 * ESCALA))
    punta = 6 * ESCALA
    draw.polygon([(x - punta, y2 - punta * 1.6), (x + punta, y2 - punta * 1.6), (x, y2)], fill=COLOR_FLECHA)


def _flecha_horizontal(draw, x1, x2, y):
    draw.line([x1, y, x2, y], fill=COLOR_FLECHA, width=int(2.5 * ESCALA))
    punta = 6 * ESCALA
    draw.polygon([(x2 - punta * 1.6, y - punta), (x2 - punta * 1.6, y + punta), (x2, y)], fill=COLOR_FLECHA)


def generar_arquitectura_capas() -> Image.Image:
    ancho_svg, alto_svg = 760 * ESCALA, 620 * ESCALA
    ancho_caja, alto_caja, x_caja = 520 * ESCALA, 80 * ESCALA, 120 * ESCALA

    capas = [
        (40, "Hardware", "CPU, RAM, almacenamiento (reales, del equipo anfitrión)", COLOR_HARDWARE),
        (150, "Firmware simulado", "firmware/firmware_simulador.py — servidor TCP, 3 variables, device_id", COLOR_FIRMWARE),
        (260, "Sistema operativo", "sockets, procesos, memoria, disco, variables de entorno (Windows/Linux)", COLOR_SO),
        (370, "Software (Python)", "hsf_app/ — adquisición, validación, procesamiento, orquestación", COLOR_PYTHON),
        (480, "Persistencia / Reporte", "data/lecturas.csv + data/reporte_ejecucion.json + logs/sistema.log", COLOR_DATOS),
    ]

    img = Image.new("RGB", (ancho_svg, alto_svg), COLOR_BLANCO)
    draw = ImageDraw.Draw(img)
    _texto_centrado(draw, ancho_svg / 2, 10 * ESCALA, "Arquitectura en capas — Práctica HSF", _fuente(18 * ESCALA, True), COLOR_TEXTO)

    for y, titulo, subtitulo, color in capas:
        _caja(draw, x_caja, y * ESCALA, ancho_caja, alto_caja, color, titulo, subtitulo)

    for i in range(len(capas) - 1):
        y1 = (capas[i][0]) * ESCALA + alto_caja
        y2 = capas[i + 1][0] * ESCALA
        _flecha_vertical(draw, x_caja + ancho_caja / 2, y1 + 2 * ESCALA, y2 - 2 * ESCALA)

    _texto_centrado(draw, ancho_svg / 2, alto_svg - 24 * ESCALA, "Fuente: el autor — generado con scripts/generar_diagramas_png.py", _fuente(11 * ESCALA), COLOR_PIE)
    return img


def generar_flujo_datos() -> Image.Image:
    ancho_svg, alto_svg = 1080 * ESCALA, 420 * ESCALA
    pasos = [
        ("Firmware simulado", "emite JSON por TCP", COLOR_FIRMWARE),
        ("acquisition.py", "lee línea, parsea JSON", COLOR_PYTHON),
        ("validation.py", "estructura, tipo, rango", COLOR_PYTHON),
        ("processing.py", "normal / anómalo", COLOR_PYTHON),
        ("persistence.py", "CSV + reporte JSON", COLOR_DATOS),
        ("logging_setup.py", "logs/sistema.log", COLOR_DATOS),
    ]
    ancho_caja, alto_caja = 160 * ESCALA, 95 * ESCALA
    espacio = 20 * ESCALA
    x = 25 * ESCALA
    y = (alto_svg - alto_caja) / 2 - 20 * ESCALA

    img = Image.new("RGB", (ancho_svg, alto_svg), COLOR_BLANCO)
    draw = ImageDraw.Draw(img)
    _texto_centrado(draw, ancho_svg / 2, 10 * ESCALA, "Flujo de una lectura, de origen a reporte", _fuente(18 * ESCALA, True), COLOR_TEXTO)

    centros = []
    for titulo, subtitulo, color in pasos:
        draw.rounded_rectangle([x, y, x + ancho_caja, y + alto_caja], radius=10 * ESCALA, fill=color)
        cx = x + ancho_caja / 2
        _texto_centrado(draw, cx, y + alto_caja / 2 - 18 * ESCALA, titulo, _fuente(13 * ESCALA, True), COLOR_BLANCO)
        _texto_centrado(draw, cx, y + alto_caja / 2 + 2 * ESCALA, subtitulo, _fuente(11 * ESCALA), COLOR_BLANCO)
        centros.append(x + ancho_caja / 2)
        x += ancho_caja + espacio

    for i in range(len(pasos) - 1):
        x1 = centros[i] + ancho_caja / 2
        x2 = centros[i + 1] - ancho_caja / 2
        _flecha_horizontal(draw, x1, x2, y + alto_caja / 2)

    _texto_centrado(
        draw, ancho_svg / 2, alto_svg - 40 * ESCALA,
        "Ante ErrorAdquisicion, ErrorValidacion o ConnectionError el ciclo continúa — no se detiene la aplicación (RF09)",
        _fuente(11 * ESCALA), COLOR_PIE,
    )
    return img


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    generar_arquitectura_capas().save(SALIDA / "arquitectura_capas.png")
    generar_flujo_datos().save(SALIDA / "flujo_datos.png")
    print(f"PNG generados en {SALIDA}")


if __name__ == "__main__":
    main()
