"""Validación de estructura, tipo y rango de las lecturas recibidas (RF03)."""

from hsf_app.config import CAMPOS_REQUERIDOS, RANGOS_VALIDOS


class ErrorValidacion(ValueError):
    """Se lanza cuando una lectura no cumple estructura, tipo o rango esperado."""


def validar_lectura(lectura: dict) -> None:
    if not isinstance(lectura, dict):
        raise ErrorValidacion(f"la lectura debe ser un dict, llegó {type(lectura).__name__}")

    for campo, tipo_esperado in CAMPOS_REQUERIDOS.items():
        if campo not in lectura:
            raise ErrorValidacion(f"falta el campo requerido: {campo}")
        if not isinstance(lectura[campo], tipo_esperado):
            raise ErrorValidacion(
                f"tipo incorrecto en {campo}: se esperaba {tipo_esperado}, "
                f"llegó {type(lectura[campo]).__name__}"
            )

    if not lectura["device_id"].strip():
        raise ErrorValidacion("device_id no puede estar vacío")

    for campo, (minimo, maximo) in RANGOS_VALIDOS.items():
        valor = lectura[campo]
        if not (minimo <= valor <= maximo):
            raise ErrorValidacion(
                f"{campo} fuera de rango válido: {valor} no está en [{minimo}, {maximo}]"
            )
