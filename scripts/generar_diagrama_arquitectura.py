"""Genera los diagramas SVG de arquitectura en capas y de flujo de datos
(Anexo 3 §5 y §7). SVG plano, sin dependencias externas, para que se
pueda regenerar con solo `python scripts/generar_diagrama_arquitectura.py`.
"""

from pathlib import Path

SALIDA = Path(__file__).resolve().parent.parent / "diagramas"

COLOR_HARDWARE = "#8d6e63"
COLOR_FIRMWARE = "#ef6c00"
COLOR_SO = "#5e35b1"
COLOR_PYTHON = "#1565c0"
COLOR_DATOS = "#2e7d32"
COLOR_TEXTO = "#1a1a1a"
COLOR_TEXTO_CLARO = "#ffffff"
COLOR_FLECHA = "#555555"


def _caja(x, y, ancho, alto, color, titulo, subtitulo="", tam_titulo=16, tam_subtitulo=12):
    partes = [f'<rect x="{x}" y="{y}" width="{ancho}" height="{alto}" rx="10" fill="{color}" />']
    partes.append(
        f'<text x="{x + ancho / 2}" y="{y + alto / 2 - (6 if subtitulo else 0)}" '
        f'text-anchor="middle" font-family="Segoe UI, Arial" font-size="{tam_titulo}" '
        f'font-weight="bold" fill="{COLOR_TEXTO_CLARO}">{titulo}</text>'
    )
    if subtitulo:
        partes.append(
            f'<text x="{x + ancho / 2}" y="{y + alto / 2 + 16}" text-anchor="middle" '
            f'font-family="Segoe UI, Arial" font-size="{tam_subtitulo}" fill="{COLOR_TEXTO_CLARO}">{subtitulo}</text>'
        )
    return "\n".join(partes)


def _flecha(x1, y1, x2, y2, etiqueta=""):
    partes = [
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{COLOR_FLECHA}" '
        f'stroke-width="2.5" marker-end="url(#punta)" />'
    ]
    if etiqueta:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 8
        partes.append(
            f'<text x="{mx}" y="{my}" text-anchor="middle" font-family="Segoe UI, Arial" '
            f'font-size="12" fill="{COLOR_TEXTO}">{etiqueta}</text>'
        )
    return "\n".join(partes)


def _definiciones():
    return """
    <defs>
      <marker id="punta" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L0,6 L9,3 z" fill="#555555" />
      </marker>
    </defs>
    """


def generar_arquitectura_capas() -> str:
    ancho_svg, alto_svg = 760, 620
    ancho_caja, alto_caja, x_caja = 520, 80, 120

    capas = [
        (40, "Hardware", "CPU, RAM, almacenamiento (reales, del equipo anfitrión)", COLOR_HARDWARE),
        (150, "Firmware simulado", "firmware/firmware_simulador.py — servidor TCP, 3 variables, device_id", COLOR_FIRMWARE),
        (260, "Sistema operativo", "sockets, procesos, memoria, disco, variables de entorno (Windows/Linux)", COLOR_SO),
        (370, "Software (Python)", "hsf_app/ — adquisición, validación, procesamiento, orquestación", COLOR_PYTHON),
        (480, "Persistencia / Reporte", "data/lecturas.csv + data/reporte_ejecucion.json + logs/sistema.log", COLOR_DATOS),
    ]

    svg = [f'<svg viewBox="0 0 {ancho_svg} {alto_svg}" xmlns="http://www.w3.org/2000/svg">']
    svg.append(_definiciones())
    svg.append(
        f'<text x="{ancho_svg/2}" y="26" text-anchor="middle" font-family="Segoe UI, Arial" '
        f'font-size="18" font-weight="bold" fill="{COLOR_TEXTO}">Arquitectura en capas — Práctica HSF</text>'
    )

    for y, titulo, subtitulo, color in capas:
        svg.append(_caja(x_caja, y, ancho_caja, alto_caja, color, titulo, subtitulo))

    for i in range(len(capas) - 1):
        y1 = capas[i][0] + alto_caja
        y2 = capas[i + 1][0]
        svg.append(_flecha(x_caja + ancho_caja / 2, y1 + 2, x_caja + ancho_caja / 2, y2 - 2))

    svg.append(
        f'<text x="{ancho_svg/2}" y="{alto_svg - 15}" text-anchor="middle" '
        f'font-family="Segoe UI, Arial" font-size="11" fill="#777777">'
        f"Fuente: el autor — generado con scripts/generar_diagrama_arquitectura.py</text>"
    )
    svg.append("</svg>")
    return "\n".join(svg)


def generar_flujo_datos() -> str:
    ancho_svg, alto_svg = 1080, 420
    pasos = [
        ("Firmware simulado", "emite JSON por TCP", COLOR_FIRMWARE),
        ("acquisition.py", "lee línea, parsea JSON", COLOR_PYTHON),
        ("validation.py", "estructura, tipo, rango", COLOR_PYTHON),
        ("processing.py", "normal / anómalo", COLOR_PYTHON),
        ("persistence.py", "CSV + reporte JSON", COLOR_DATOS),
        ("logging_setup.py", "logs/sistema.log", COLOR_DATOS),
    ]
    ancho_caja, alto_caja = 160, 95
    espacio = 20
    x = 25
    y = (alto_svg - alto_caja) / 2 - 20

    svg = [f'<svg viewBox="0 0 {ancho_svg} {alto_svg}" xmlns="http://www.w3.org/2000/svg">']
    svg.append(_definiciones())
    svg.append(
        f'<text x="{ancho_svg/2}" y="28" text-anchor="middle" font-family="Segoe UI, Arial" '
        f'font-size="18" font-weight="bold" fill="{COLOR_TEXTO}">Flujo de una lectura, de origen a reporte</text>'
    )

    centros = []
    for titulo, subtitulo, color in pasos:
        svg.append(_caja(x, y, ancho_caja, alto_caja, color, titulo, subtitulo, tam_titulo=13, tam_subtitulo=11))
        centros.append((x + ancho_caja / 2, y))
        x += ancho_caja + espacio

    for i in range(len(pasos) - 1):
        x1 = centros[i][0] + ancho_caja / 2
        x2 = centros[i + 1][0] - ancho_caja / 2
        y_mid = y + alto_caja / 2
        svg.append(_flecha(x1, y_mid, x2, y_mid))

    svg.append(
        f'<text x="{ancho_svg/2}" y="{alto_svg - 15}" text-anchor="middle" '
        f'font-family="Segoe UI, Arial" font-size="11" fill="#777777">'
        f"Ante ErrorAdquisicion, ErrorValidacion o ConnectionError el ciclo continúa — no se detiene la aplicación (RF09)</text>"
    )
    svg.append("</svg>")
    return "\n".join(svg)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "arquitectura_capas.svg").write_text(generar_arquitectura_capas(), encoding="utf-8")
    (SALIDA / "flujo_datos.svg").write_text(generar_flujo_datos(), encoding="utf-8")
    print(f"Diagramas generados en {SALIDA}")


if __name__ == "__main__":
    main()
